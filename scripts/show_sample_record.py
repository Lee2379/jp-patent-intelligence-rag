#!/usr/bin/env python3
"""Print one compressed Japanese patent record as a screenshot-friendly excerpt."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "curated" / "stratified_1pct"


def find_record(dataset_dir: Path, year: str, document_id: str) -> dict:
    source_file = dataset_dir / f"{year}.jsonl.gz"
    if not source_file.exists():
        raise FileNotFoundError(f"Dataset file not found: {source_file}")

    with gzip.open(source_file, "rt", encoding="utf-8") as records:
        for line in records:
            record = json.loads(line)
            local_path = record.get("meta", {}).get("local_path", "")
            if document_id in local_path:
                return record

    raise LookupError(f"Document {document_id} was not found in {source_file.name}")


def extract_section(text: str, start: str, end_patterns: list[str]) -> str:
    start_position = text.find(start)
    if start_position < 0:
        return "[section not found]"

    content_start = start_position + len(start)
    candidates = []
    for end_pattern in end_patterns:
        match = re.search(end_pattern, text[content_start:], flags=re.DOTALL)
        if match:
            candidates.append(content_start + match.start())

    content_end = min(candidates) if candidates else len(text)
    return text[content_start:content_end]


def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^\s*\(57\)\s*", "", text)
    return text.strip()


def wrapped_lines(text: str, width: int, max_chars: int) -> list[str]:
    clipped = normalize(text)[:max_chars]
    if len(normalize(text)) > max_chars:
        clipped += " …"
    return textwrap.wrap(
        clipped,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
    )


def format_record(record: dict, year: str, document_id: str, width: int) -> str:
    text = record.get("text", "")
    local_path = record.get("meta", {}).get("local_path", "")

    abstract = extract_section(
        text,
        "【要約】",
        [r"\d{10}\.tif", r"【特許請求の範囲】"],
    )
    claim_1 = extract_section(
        text,
        "【請求項１】",
        [r"【請求項２】", r"【発明の詳細な説明】"],
    )

    lines = [
        "Japanese Patent Raw Record",
        "=" * 72,
        f"Source year      : {year}",
        "Publication kind : A (公開特許公報)",
        f"Document ID     : {document_id}",
        "",
        "【要約】",
    ]
    lines.extend(wrapped_lines(abstract, width, max_chars=520))
    lines.extend(["", "【特許請求の範囲】", "【請求項１】"])
    lines.extend(wrapped_lines(claim_1, width, max_chars=650))
    lines.extend(["", "meta.local_path:", local_path])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default="2020")
    parser.add_argument("--document-id", default="2020151139")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--width", type=int, default=72)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    record = find_record(args.dataset_dir, args.year, args.document_id)
    rendered = format_record(record, args.year, args.document_id, args.width)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Saved: {args.output}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
