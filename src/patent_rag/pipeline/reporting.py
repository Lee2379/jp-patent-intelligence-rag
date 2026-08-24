from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _percent(value: int, total: int) -> float:
    return round(value / total * 100, 1) if total else 0.0


def build_data_quality_report(data_quality_path: Path, output_path: Path) -> None:
    report = json.loads(data_quality_path.read_text(encoding="utf-8"))
    total = int(report["documents_written"])
    year_rows = "".join(
        f"<tr><td>{year}</td><td>{count:,}</td><td><div class='bar'><i style='width:{_percent(count, total)}%'></i></div></td><td>{_percent(count, total)}%</td></tr>"
        for year, count in report["year_distribution"].items()
    )
    section_rows = "".join(
        f"<tr><td>{html.escape(section)}</td><td>{count:,}</td><td><div class='bar'><i style='width:{_percent(count, total)}%'></i></div></td><td>{_percent(count, total)}%</td></tr>"
        for section, count in list(report["section_coverage"].items())[:10]
    )
    examples = "".join(
        f"<article><span>JP {html.escape(str(item['document_id']))} · {item['year']}</span><b>AI score {item['ai_score']}</b><p>{html.escape(item['abstract_preview'])}</p></article>"
        for item in report["sample_ai_documents"][:4]
    )
    document = f"""<!doctype html><html lang='ja'><head><meta charset='utf-8'><title>Data Quality Report</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0b0d0e;color:#f3f1e8;font-family:Inter,'Yu Gothic UI',sans-serif}}main{{width:1120px;max-width:calc(100% - 48px);margin:auto;padding:56px 0 80px}}header{{display:flex;justify-content:space-between;border-bottom:1px solid #303433;padding-bottom:20px}}.tag{{color:#c8ff43;font:700 11px monospace;letter-spacing:.15em}}h1{{font-size:56px;letter-spacing:-.05em;margin:38px 0 8px}}.sub{{color:#a7aaa5}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#303433;margin:42px 0}}.kpis div{{background:#121516;padding:22px}}.kpis span{{display:block;color:#848783;font:10px monospace;letter-spacing:.1em}}.kpis b{{display:block;font-size:30px;margin-top:18px}}.ok{{color:#c8ff43}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}section{{border:1px solid #303433;background:#121516;padding:24px}}h2{{font-size:13px;letter-spacing:.1em;margin:0 0 22px}}table{{width:100%;border-collapse:collapse;font-size:12px}}td{{padding:10px 6px;border-top:1px solid #262a2a}}td:nth-child(2),td:last-child{{text-align:right;font-family:monospace}}.bar{{width:130px;height:4px;background:#292d2c}}.bar i{{display:block;height:100%;background:#c8ff43}}.examples{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}}article{{border:1px solid #303433;padding:18px;background:#121516}}article span{{font:700 11px monospace;color:#c8ff43}}article b{{float:right;color:#ff714b;font:10px monospace}}article p{{color:#b6b8b2;font-size:12px;line-height:1.7}}footer{{margin-top:28px;color:#6f736f;font:10px monospace}}
</style></head><body><main><header><strong>JP PATENT INTELLIGENCE</strong><span class='tag'>PIPELINE / DATA QUALITY</span></header><h1>46K patents. Zero silent failures.</h1><p class='sub'>Year-stratified Japanese public patent applications → normalized, parsed, and AI-domain selected.</p><div class='kpis'><div><span>DOCUMENTS WRITTEN</span><b>{total:,}</b></div><div><span>VALID JSON</span><b class='ok'>{_percent(total, int(report["documents_seen"]))}%</b></div><div><span>AI DOCUMENTS</span><b>{report["ai_documents_selected"]:,}</b></div><div><span>EVIDENCE CHUNKS</span><b>{report["ai_chunks_written"]:,}</b></div></div><div class='grid'><section><h2>YEAR DISTRIBUTION</h2><table>{year_rows}</table></section><section><h2>SECTION EXTRACTION COVERAGE</h2><table>{section_rows}</table></section></div><div class='examples'>{examples}</div><footer>NII LLM-jp Corpus v4 Japanese patents · CC BY 4.0 · deterministic local pipeline v{report["pipeline_version"]}</footer></main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def build_evaluation_report(results: dict[str, Any], output_path: Path) -> None:
    methods = ["bm25", "dense", "hybrid"]
    colors = {"bm25": "#ff714b", "dense": "#5ac8fa", "hybrid": "#c8ff43"}
    cards = "".join(
        f"<article><span>{method.upper()}</span><strong>{results['metrics'][method]['mrr_at_10']:.3f}</strong><small>MRR@10</small><div class='bar'><i style='width:{results['metrics'][method]['recall_at_5'] * 100:.1f}%;background:{colors[method]}'></i></div><b>Recall@5 {results['metrics'][method]['recall_at_5']:.1%}</b></article>"
        for method in methods
    )
    rows = "".join(
        f"<tr><td>{html.escape(item['query'])}</td><td>JP {item['expected_document_id']}</td><td>{item['hybrid_rank'] or '—'}</td></tr>"
        for item in results["cases"][:12]
    )
    multilingual = results.get("multilingual_benchmark")
    multilingual_summary = ""
    if multilingual:
        multi_metrics = multilingual["metrics"]
        multilingual_summary = f"""<aside><div><span>CURATED KO / EN CHECK</span><strong>{multilingual["query_count"]} QUERIES</strong></div><div><span>BM25 RECALL@5</span><strong>{multi_metrics["bm25"]["recall_at_5"]:.1%}</strong></div><div><span>DENSE RECALL@5</span><strong>{multi_metrics["dense"]["recall_at_5"]:.1%}</strong></div><div><span>HYBRID RECALL@5</span><strong>{multi_metrics["hybrid"]["recall_at_5"]:.1%}</strong></div></aside>"""
    document = f"""<!doctype html><html lang='ja'><head><meta charset='utf-8'><title>Retrieval Evaluation</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#0b0d0e;color:#f3f1e8;font-family:Inter,'Yu Gothic UI',sans-serif}}main{{width:1120px;max-width:calc(100% - 48px);margin:auto;padding:56px 0}}header{{display:flex;justify-content:space-between;border-bottom:1px solid #303433;padding-bottom:20px}}.tag{{color:#c8ff43;font:700 11px monospace;letter-spacing:.15em}}h1{{font-size:56px;letter-spacing:-.05em;margin:38px 0 8px}}p{{color:#a7aaa5}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#303433;margin:40px 0 18px}}article{{background:#121516;padding:24px}}article span,aside span{{font:700 11px monospace;color:#858985}}article strong{{display:block;font-size:44px;margin:22px 0 0}}article small{{color:#858985}}.bar{{height:6px;background:#292d2c;margin:24px 0 9px}}.bar i{{display:block;height:100%}}article b{{font:600 11px monospace}}aside{{display:grid;grid-template-columns:1.6fr repeat(3,1fr);gap:1px;background:#303433;margin-bottom:28px}}aside div{{background:#121516;padding:17px 20px}}aside span{{display:block}}aside strong{{display:block;margin-top:8px;color:#c8ff43;font:700 16px monospace}}section{{border:1px solid #303433;background:#121516;padding:24px}}h2{{font-size:13px;letter-spacing:.1em}}table{{width:100%;border-collapse:collapse;font-size:12px}}td{{padding:12px 8px;border-top:1px solid #292d2c}}td:first-child{{width:65%;color:#c5c7c1}}td:nth-child(2),td:last-child{{font-family:monospace;text-align:right}}footer{{margin-top:24px;color:#6f736f;font:10px monospace}}
</style></head><body><main><header><strong>JP PATENT INTELLIGENCE</strong><span class='tag'>RETRIEVAL / SILVER BENCHMARK</span></header><h1>Hybrid retrieval, measured.</h1><p>{results["query_count"]} abstract-problem queries · document-level relevance · deterministic evaluation.</p><div class='cards'>{cards}</div>{multilingual_summary}<section><h2>EVALUATION CASES / HYBRID RANK</h2><table>{rows}</table></section><footer>The 30-query set is abstract-derived silver evidence; the six-query KO/EN set is a manually curated smoke check. Neither is a legal relevance judgment. Generated {html.escape(results["generated_at"])}.</footer></main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
