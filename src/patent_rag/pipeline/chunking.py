from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from patent_rag.models import PatentChunk, PatentDocument


def _stable_chunk_id(document_id: str, section: str, ordinal: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    return f"JP-{document_id}-{section}-{ordinal:03d}-{digest}"


def split_japanese_text(text: str, max_chars: int = 600, overlap_chars: int = 80) -> list[str]:
    """Sentence-aware character chunks; Japanese text cannot rely on spaces."""
    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []
    sentences = [part.strip() for part in re.split(r"(?<=[。！？])\s*|\n+", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(sentence):
                end = min(start + max_chars, len(sentence))
                chunks.append(sentence[start:end])
                if end == len(sentence):
                    break
                start = max(end - overlap_chars, start + 1)
            continue
        if current and len(current) + len(sentence) > max_chars:
            chunks.append(current)
            overlap = current[-overlap_chars:]
            candidate = f"{overlap}{sentence}"
            current = candidate if len(candidate) <= max_chars else sentence
        else:
            current = f"{current}{sentence}"
    if current:
        chunks.append(current)
    if any(len(chunk) > max_chars for chunk in chunks):
        raise AssertionError("Chunking invariant violated: chunk exceeds max_chars")
    return chunks


def chunk_document(document: PatentDocument) -> list[PatentChunk]:
    source_sections: list[tuple[str, str]] = []
    if document.abstract:
        source_sections.append(("abstract", document.abstract))
    source_sections.extend(
        (f"claim_{index}", claim) for index, claim in enumerate(document.claims, 1)
    )
    source_sections.extend((section.name, section.text) for section in document.sections)

    chunks: list[PatentChunk] = []
    ordinal = 0
    for section_name, section_text in source_sections:
        safe_section = re.sub(r"[^0-9A-Za-z一-龯ぁ-んァ-ヶ]+", "_", section_name).strip("_")
        for piece in split_japanese_text(section_text):
            ordinal += 1
            chunks.append(
                PatentChunk(
                    chunk_id=_stable_chunk_id(document.document_id, safe_section, ordinal, piece),
                    document_id=document.document_id,
                    year=document.year,
                    publication_kind=document.publication_kind,
                    section=section_name,
                    text=piece,
                    local_path=document.local_path,
                    ai_score=document.ai_score,
                    ordinal=ordinal,
                )
            )
    return chunks


def chunk_documents(documents: Iterable[PatentDocument]) -> Iterable[PatentChunk]:
    for document in documents:
        yield from chunk_document(document)
