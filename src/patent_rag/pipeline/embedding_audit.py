from __future__ import annotations

import gzip
import hashlib
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from tokenizers import Tokenizer
from tqdm.auto import tqdm


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_embedding_context_report(result: dict[str, Any], output_path: Path) -> None:
    tokens = result["tokens"]
    token_limit = int(result["token_limit"])

    def width(value: float) -> str:
        return f"{min(value / token_limit * 100, 100):.1f}%"

    rows = "".join(
        f"<div class='row'><span>{label}</span><div class='track'><i style='width:{width(value)}'></i></div><b>{value:g}</b></div>"
        for label, value in (
            ("MEDIAN", float(tokens["median"])),
            ("P95", float(tokens["p95"])),
            ("P99", float(tokens["p99"])),
            ("MAX", float(tokens["max"])),
        )
    )
    accepted = bool(result["accepted"])
    status = "PASS" if accepted else "FAIL"
    status_class = "pass" if accepted else "fail"
    model = html.escape(str(result["tokenizer_model"]))
    source_hash = html.escape(str(result["chunks_sha256"]))
    document = f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Embedding Context Audit</title><style>
:root{{--bg:#11130f;--panel:#1a1d17;--line:#34392c;--text:#f0f2e8;--muted:#a5aa98;--accent:#c8ff38;--fail:#ff736f}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 80% 0,#263018 0,transparent 36%),var(--bg);color:var(--text);font-family:Inter,Arial,sans-serif}}
main{{width:min(1120px,92vw);margin:38px auto 64px}}header{{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:18px;font:700 12px monospace;letter-spacing:.14em}}
.tag{{color:var(--accent)}}h1{{font-size:clamp(38px,6vw,72px);line-height:.96;letter-spacing:-.055em;margin:58px 0 16px;max-width:900px}}.sub{{color:var(--muted);font-size:17px;max-width:760px;line-height:1.55}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin:42px 0}}.kpis div{{background:var(--panel);padding:24px}}.kpis span{{display:block;color:var(--muted);font:700 11px monospace;letter-spacing:.12em}}.kpis b{{display:block;font-size:35px;margin-top:12px}}.kpis b.pass{{color:var(--accent)}}.kpis b.fail{{color:var(--fail)}}
.grid{{display:grid;grid-template-columns:1.6fr 1fr;gap:22px}}section{{border:1px solid var(--line);background:rgba(26,29,23,.88);padding:28px}}h2{{font:700 12px monospace;letter-spacing:.14em;margin:0 0 28px;color:var(--muted)}}.row{{display:grid;grid-template-columns:70px 1fr 56px;gap:14px;align-items:center;margin:22px 0;font:700 12px monospace}}.track{{height:10px;background:#303529;overflow:hidden}}.track i{{display:block;height:100%;background:var(--accent)}}.row b{{text-align:right;font-size:15px}}dl{{margin:0}}dt{{color:var(--muted);font:700 10px monospace;letter-spacing:.12em;margin-top:20px}}dd{{margin:7px 0 0;line-height:1.45;word-break:break-all}}footer{{color:var(--muted);border-top:1px solid var(--line);margin-top:28px;padding-top:18px;font:11px monospace}}
@media(max-width:760px){{.kpis,.grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:500px){{.kpis,.grid{{grid-template-columns:1fr}}}}
</style></head><body><main><header><strong>JP PATENT INTELLIGENCE</strong><span class='tag'>EMBEDDING / CONTEXT QUALITY GATE</span></header>
<h1>{int(result["chunks"]):,} chunks.<br>Zero silent truncation.</h1><p class='sub'>Every persisted Japanese patent passage was tokenized with the production embedding tokenizer and required passage prefix before the dense index was accepted.</p>
<div class='kpis'><div><span>CONTEXT LIMIT</span><b>{token_limit}</b></div><div><span>MAX OBSERVED</span><b>{int(tokens["max"])}</b></div><div><span>OVER LIMIT</span><b>{int(result["over_limit"])}</b></div><div><span>QUALITY GATE</span><b class='{status_class}'>{status}</b></div></div>
<div class='grid'><section><h2>TOKEN DISTRIBUTION / LIMIT {token_limit}</h2>{rows}</section><section><h2>REPRODUCIBILITY</h2><dl><dt>MODEL</dt><dd>{model}</dd><dt>INPUT CONTRACT</dt><dd>passage: &lt;Japanese patent section&gt;</dd><dt>CHARACTER CAP</dt><dd>600 characters</dd><dt>CHUNKS SHA-256</dt><dd>{source_hash}</dd></dl></section></div>
<footer>Full-corpus deterministic audit · no sampling · generated locally · required service cost $0</footer></main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def audit_embedding_context(
    chunks_path: Path,
    output_path: Path,
    *,
    tokenizer_model: str = "intfloat/multilingual-e5-small",
    token_limit: int = 512,
    passage_prefix: str = "passage: ",
) -> dict[str, Any]:
    """Measure token-window fit on every persisted evidence chunk without truncation."""
    tokenizer = Tokenizer.from_pretrained(tokenizer_model)
    tokenizer.no_truncation()
    token_counts: list[int] = []
    character_counts: list[int] = []
    examples_over_limit: list[dict[str, Any]] = []

    with gzip.open(chunks_path, "rt", encoding="utf-8") as handle:
        for line in tqdm(handle, desc="Auditing embedding context"):
            chunk = json.loads(line)
            text = str(chunk["text"])
            token_count = len(tokenizer.encode(f"{passage_prefix}{text}").ids)
            token_counts.append(token_count)
            character_counts.append(len(text))
            if token_count > token_limit and len(examples_over_limit) < 5:
                examples_over_limit.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "section": chunk["section"],
                        "characters": len(text),
                        "tokens": token_count,
                    }
                )

    if not token_counts:
        raise ValueError(f"No chunks found in {chunks_path}")
    tokens = np.asarray(token_counts)
    characters = np.asarray(character_counts)
    over_limit = int(np.count_nonzero(tokens > token_limit))
    result: dict[str, Any] = {
        "audit_version": "0.1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "chunks_path": chunks_path.as_posix(),
        "chunks_sha256": _sha256(chunks_path),
        "tokenizer_model": tokenizer_model,
        "passage_prefix": passage_prefix,
        "token_limit": token_limit,
        "chunks": len(token_counts),
        "characters": {
            "median": float(np.median(characters)),
            "p95": float(np.percentile(characters, 95)),
            "max": int(np.max(characters)),
        },
        "tokens": {
            "median": float(np.median(tokens)),
            "p95": float(np.percentile(tokens, 95)),
            "p99": float(np.percentile(tokens, 99)),
            "max": int(np.max(tokens)),
        },
        "over_limit": over_limit,
        "over_limit_percent": round(100 * over_limit / len(token_counts), 4),
        "accepted": over_limit == 0,
        "examples_over_limit": examples_over_limit,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    build_embedding_context_report(result, output_path.with_suffix(".html"))
    return result
