from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patent_rag.pipeline.reporting import build_evaluation_report
from patent_rag.retrieval.bm25 import RankedItem
from patent_rag.retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion
from patent_rag.retrieval.query_expansion import expand_sparse_query


def _problem_query(text: str) -> str | None:
    match = re.search(r"【課題】(.+?)(?:【解決手段】|$)", text, flags=re.DOTALL)
    if not match:
        return None
    problem = " ".join(match.group(1).split())
    if not 30 <= len(problem) <= 500:
        return None
    return f"次の技術的課題を解決する発明を検索してください: {problem}"


def build_silver_queries(retriever: HybridRetriever, count: int = 30) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk in retriever.chunks:
        document_id = str(chunk["document_id"])
        if chunk["section"] != "abstract" or document_id in seen:
            continue
        query = _problem_query(str(chunk["text"]))
        if query:
            seen.add(document_id)
            candidates.append({"query": query, "expected_document_id": document_id})
    if len(candidates) < count:
        count = len(candidates)
    if count == 0:
        raise ValueError("No abstract problem statements were available for evaluation")
    step = max(len(candidates) // count, 1)
    return candidates[::step][:count]


def _document_ranks(items: list[Any], chunks: list[dict[str, Any]]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for item in items:
        document_id = str(chunks[item.index]["document_id"])
        if document_id not in ranks:
            ranks[document_id] = len(ranks) + 1
    return ranks


def _metrics(ranks: list[int | None]) -> dict[str, float]:
    total = len(ranks)
    return {
        "recall_at_1": sum(rank == 1 for rank in ranks) / total,
        "recall_at_5": sum(rank is not None and rank <= 5 for rank in ranks) / total,
        "recall_at_10": sum(rank is not None and rank <= 10 for rank in ranks) / total,
        "mrr_at_10": sum(1 / rank for rank in ranks if rank is not None and rank <= 10) / total,
    }


def _evaluate_cases(
    retriever: HybridRetriever,
    cases: list[dict[str, str]],
) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]]]:
    method_ranks: dict[str, list[int | None]] = {"bm25": [], "dense": [], "hybrid": []}
    evaluated_cases: list[dict[str, Any]] = []
    for case in cases:
        sparse_query, expansion_terms = expand_sparse_query(case["query"])
        sparse = retriever.bm25.search(sparse_query, top_k=50)
        dense = retriever.dense.search(case["query"], top_k=50)
        fused = reciprocal_rank_fusion([sparse, dense])
        fused_items = [
            RankedItem(index=index, score=score, rank=rank)
            for rank, (index, score) in enumerate(fused, 1)
        ]
        rankings = {
            "bm25": _document_ranks(sparse, retriever.chunks),
            "dense": _document_ranks(dense, retriever.chunks),
            "hybrid": _document_ranks(fused_items, retriever.chunks),
        }
        expected = case["expected_document_id"]
        for method in method_ranks:
            method_ranks[method].append(rankings[method].get(expected))
        evaluated_cases.append(
            {
                **case,
                "sparse_expansion_terms": expansion_terms,
                "bm25_rank": rankings["bm25"].get(expected),
                "dense_rank": rankings["dense"].get(expected),
                "hybrid_rank": rankings["hybrid"].get(expected),
            }
        )
    return (
        {method: _metrics(ranks) for method, ranks in method_ranks.items()},
        evaluated_cases,
    )


def evaluate_retrieval(
    retriever: HybridRetriever,
    output_dir: Path,
    query_count: int = 30,
    multilingual_queries_path: Path | None = None,
) -> dict[str, Any]:
    queries = build_silver_queries(retriever, query_count)
    metrics, cases = _evaluate_cases(retriever, queries)
    results: dict[str, Any] = {
        "benchmark": "abstract-problem silver retrieval",
        "generated_at": datetime.now(UTC).isoformat(),
        "query_count": len(queries),
        "metrics": metrics,
        "cases": cases,
        "limitations": [
            "Queries come from source abstracts; this measures retrieval sanity, "
            "not expert legal relevance.",
            "The source document is the target; equivalent patents are not exhaustively labeled.",
        ],
    }
    if multilingual_queries_path is not None and multilingual_queries_path.exists():
        multilingual_queries = json.loads(multilingual_queries_path.read_text(encoding="utf-8"))
        multilingual_metrics, multilingual_cases = _evaluate_cases(retriever, multilingual_queries)
        results["multilingual_benchmark"] = {
            "benchmark": "manually curated Korean/English smoke benchmark",
            "query_count": len(multilingual_queries),
            "metrics": multilingual_metrics,
            "cases": multilingual_cases,
            "limitations": [
                "The set contains six regression queries over three known documents.",
                "It is a multilingual capability check, not a statistically powered benchmark.",
            ],
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "retrieval_evaluation.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_evaluation_report(results, output_dir / "retrieval_evaluation.html")
    return results
