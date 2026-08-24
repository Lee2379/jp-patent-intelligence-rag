from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath

from patent_rag.models import PatentDocument, PatentSection

MARKER_PATTERN = re.compile(r"【([^】]+)】")
CLAIM_PATTERN = re.compile(r"【請求項\s*([0-9０-９]+)】")
PARAGRAPH_PATTERN = re.compile(r"【[0-9０-９]{4}】")

SECTION_ALIASES = {
    "技術分野": "技術分野",
    "発明の属する技術分野": "技術分野",
    "背景技術": "背景技術",
    "従来の技術": "背景技術",
    "先行技術文献": "先行技術文献",
    "特許文献": "特許文献",
    "非特許文献": "非特許文献",
    "発明の概要": "発明の概要",
    "発明が解決しようとする課題": "発明が解決しようとする課題",
    "発明の目的": "発明が解決しようとする課題",
    "課題を解決するための手段": "課題を解決するための手段",
    "発明の構成": "課題を解決するための手段",
    "作用": "作用",
    "発明の効果": "発明の効果",
    "図面の簡単な説明": "図面の簡単な説明",
    "発明を実施するための形態": "発明を実施するための形態",
    "発明の実施の形態": "発明を実施するための形態",
    "実施例": "実施例",
    "符号の説明": "符号の説明",
}

AI_TERMS: dict[str, int] = {
    "人工知能": 5,
    "機械学習": 5,
    "深層学習": 5,
    "ディープラーニング": 5,
    "ニューラルネットワーク": 4,
    "自然言語処理": 5,
    "強化学習": 5,
    "生成モデル": 4,
    "学習モデル": 3,
    "推論モデル": 3,
    "予測モデル": 2,
    "分類器": 2,
    "特徴量": 2,
    "知識グラフ": 4,
    "情報検索": 2,
}


def normalize_text(text: str) -> str:
    """Normalize width and whitespace while preserving paragraph boundaries."""
    text = unicodedata.normalize("NFKC", text).replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _between(text: str, start: str, end_markers: tuple[str, ...]) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    content_start = start_index + len(start)
    ends = [text.find(marker, content_start) for marker in end_markers]
    valid_ends = [position for position in ends if position >= 0]
    content_end = min(valid_ends) if valid_ends else len(text)
    return text[content_start:content_end].strip()


def extract_abstract(text: str) -> str:
    abstract = _between(
        text,
        "【要約】",
        ("【特許請求の範囲】", "【発明の詳細な説明】"),
    )
    lines = abstract.splitlines()
    if lines and ".tif" in lines[-1] and re.search(r"\.tif\s*\d+\s*$", lines[-1]):
        lines.pop()
    return "\n".join(lines).strip()


def extract_claims(text: str) -> list[str]:
    claim_block = _between(
        text,
        "【特許請求の範囲】",
        ("【発明の詳細な説明】", "【図面】"),
    )
    matches = list(CLAIM_PATTERN.finditer(claim_block))
    claims: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(claim_block)
        claim_number = unicodedata.normalize("NFKC", match.group(1))
        body = claim_block[match.end() : end].strip()
        if body:
            claims.append(f"【請求項{claim_number}】\n{body}")
    return claims


def extract_description_sections(text: str) -> list[PatentSection]:
    description = _between(text, "【発明の詳細な説明】", ("【図面】",))
    markers = [
        marker
        for marker in MARKER_PATTERN.finditer(description)
        if marker.group(1).strip() in SECTION_ALIASES
    ]
    sections: list[PatentSection] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(description)
        name = SECTION_ALIASES[marker.group(1).strip()]
        body = description[marker.end() : end].strip()
        body = PARAGRAPH_PATTERN.sub("\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if body:
            sections.append(PatentSection(name=name, text=body))
    return sections


def score_ai_relevance(abstract: str, claims: list[str], full_text: str) -> int:
    """High-recall deterministic AI-domain score used to define the demo corpus."""
    claim_text = "\n".join(claims)
    score = 0
    for term, weight in AI_TERMS.items():
        if term in abstract:
            score += weight * 3
        if term in claim_text:
            score += weight * 2
        if term in full_text:
            score += weight
    return score


def source_identity(local_path: str) -> tuple[str, int, str]:
    path = PurePosixPath(local_path)
    parts = path.parts
    try:
        dataset_index = parts.index("dataset")
        year = int(parts[dataset_index + 1])
        publication_kind = parts[dataset_index + 2]
    except (ValueError, IndexError):
        year_match = re.search(r"(?:19|20)\d{2}", local_path)
        year = int(year_match.group()) if year_match else 0
        publication_kind = "UNKNOWN"
    document_match = re.search(r"(\d+)\.xml\.html\.txt$", path.name)
    document_id = document_match.group(1) if document_match else path.stem.split(".")[0]
    return document_id, year, publication_kind


def parse_patent(raw_text: str, local_path: str) -> PatentDocument:
    text = normalize_text(raw_text)
    document_id, year, publication_kind = source_identity(local_path)
    abstract = extract_abstract(text)
    claims = extract_claims(text)
    sections = extract_description_sections(text)
    return PatentDocument(
        document_id=document_id,
        year=year,
        publication_kind=publication_kind,
        local_path=local_path,
        abstract=abstract,
        claims=claims,
        sections=sections,
        ai_score=score_ai_relevance(abstract, claims, text),
    )
