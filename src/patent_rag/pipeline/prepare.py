from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from patent_rag.parsing.japanese_patent import parse_patent
from patent_rag.pipeline.chunking import chunk_document


def _write_jsonl_line(handle: Any, value: dict[str, Any]) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def prepare_corpus(
    input_dir: Path,
    output_dir: Path,
    ai_threshold: int = 5,
    limit: int | None = None,
    progress_every: int = 2_000,
) -> dict[str, Any]:
    """Validate, normalize, parse and chunk every curated gzip JSONL record."""
    output_dir.mkdir(parents=True, exist_ok=True)
    documents_path = output_dir / "patents.jsonl.gz"
    chunks_path = output_dir / "chunks_ai.jsonl.gz"
    report_path = output_dir / "data_quality.json"

    total = invalid = empty_text = selected = chunk_count = 0
    years: Counter[int] = Counter()
    section_coverage: Counter[str] = Counter()
    ai_score_histogram: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    input_files = sorted(input_dir.glob("*.jsonl.gz"))
    if not input_files:
        raise FileNotFoundError(f"No .jsonl.gz files found in {input_dir}")

    with (
        gzip.open(documents_path, "wt", encoding="utf-8", newline="\n") as docs_out,
        gzip.open(chunks_path, "wt", encoding="utf-8", newline="\n") as chunks_out,
    ):
        stop = False
        for input_path in input_files:
            with gzip.open(input_path, "rt", encoding="utf-8") as source:
                for line in source:
                    if limit is not None and total >= limit:
                        stop = True
                        break
                    total += 1
                    try:
                        raw = json.loads(line)
                        text = raw.get("text", "")
                        local_path = raw.get("meta", {}).get("local_path", "")
                        if not text:
                            empty_text += 1
                            continue
                        document = parse_patent(text, local_path)
                    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                        invalid += 1
                        continue

                    _write_jsonl_line(docs_out, document.to_dict())
                    years[document.year] += 1
                    if document.abstract:
                        section_coverage["abstract"] += 1
                    if document.claims:
                        section_coverage["claims"] += 1
                    for section in {item.name for item in document.sections}:
                        section_coverage[section] += 1

                    bucket = (
                        "0" if document.ai_score == 0 else "1-4" if document.ai_score < 5 else "5+"
                    )
                    ai_score_histogram[bucket] += 1
                    if document.ai_score >= ai_threshold:
                        selected += 1
                        chunks = chunk_document(document)
                        chunk_count += len(chunks)
                        for chunk in chunks:
                            _write_jsonl_line(chunks_out, chunk.to_dict())
                        if len(examples) < 10:
                            examples.append(
                                {
                                    "document_id": document.document_id,
                                    "year": document.year,
                                    "ai_score": document.ai_score,
                                    "abstract_preview": document.abstract[:220],
                                }
                            )
                    if progress_every and total % progress_every == 0:
                        docs_out.flush()
                        chunks_out.flush()
                        print(
                            f"processed={total:,} ai_documents={selected:,} chunks={chunk_count:,}",
                            file=sys.stderr,
                            flush=True,
                        )
            if stop:
                break

    report: dict[str, Any] = {
        "pipeline_version": "0.1.0",
        "source_files": [path.name for path in input_files],
        "documents_seen": total,
        "documents_written": total - invalid - empty_text,
        "invalid_records": invalid,
        "empty_text_records": empty_text,
        "year_distribution": dict(sorted(years.items())),
        "section_coverage": dict(section_coverage.most_common()),
        "ai_threshold": ai_threshold,
        "ai_documents_selected": selected,
        "ai_chunks_written": chunk_count,
        "ai_score_histogram": dict(ai_score_histogram),
        "sample_ai_documents": examples,
        "outputs": {
            "documents": documents_path.name,
            "chunks": chunks_path.name,
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
