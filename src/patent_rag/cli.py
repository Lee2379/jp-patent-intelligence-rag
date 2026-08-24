from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _prepare(args: argparse.Namespace) -> None:
    from patent_rag.pipeline.prepare import prepare_corpus

    report = prepare_corpus(
        Path(args.input),
        Path(args.output),
        ai_threshold=args.ai_threshold,
        limit=args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _build_index(args: argparse.Namespace) -> None:
    from patent_rag.retrieval.hybrid import build_hybrid_index

    manifest = build_hybrid_index(
        Path(args.chunks),
        Path(args.output),
        embedding_model=args.embedding_model,
        cache_dir=Path(args.cache),
        max_chunks=args.max_chunks,
        batch_size=args.batch_size,
        embedding_threads=args.embedding_threads,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def _search(args: argparse.Namespace) -> None:
    from patent_rag.retrieval.hybrid import HybridRetriever

    retriever = HybridRetriever.load(Path(args.index), cache_dir=Path(args.cache))
    hits = retriever.search(args.query, top_k=args.top_k)
    result = [
        {
            "rank": hit.rank,
            "rrf_score": round(hit.score, 6),
            "sparse_score": hit.sparse_score,
            "dense_score": hit.dense_score,
            "document_id": hit.chunk["document_id"],
            "year": hit.chunk["year"],
            "section": hit.chunk["section"],
            "text": hit.chunk["text"][:500],
        }
        for hit in hits
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _report(args: argparse.Namespace) -> None:
    from patent_rag.pipeline.reporting import build_data_quality_report

    build_data_quality_report(Path(args.data_quality), Path(args.output))
    print(f"Wrote {args.output}")


def _evaluate(args: argparse.Namespace) -> None:
    from patent_rag.retrieval.evaluation import evaluate_retrieval
    from patent_rag.retrieval.hybrid import HybridRetriever

    retriever = HybridRetriever.load(Path(args.index), cache_dir=Path(args.cache))
    result = evaluate_retrieval(
        retriever,
        Path(args.output),
        query_count=args.queries,
        multilingual_queries_path=Path(args.multilingual_queries),
    )
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


def _audit_embedding(args: argparse.Namespace) -> None:
    from patent_rag.pipeline.embedding_audit import audit_embedding_context

    result = audit_embedding_context(
        Path(args.chunks),
        Path(args.output),
        tokenizer_model=args.tokenizer_model,
        token_limit=args.token_limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _verify_audit(args: argparse.Namespace) -> None:
    from patent_rag.audit import AuditStore

    result = AuditStore(Path(args.database)).verify_chain()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="patent-rag")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Parse and chunk the curated Japanese patents")
    prepare.add_argument("--input", default="data/curated/stratified_1pct")
    prepare.add_argument("--output", default="data/processed")
    prepare.add_argument("--ai-threshold", type=int, default=5)
    prepare.add_argument("--limit", type=int)
    prepare.set_defaults(func=_prepare)

    build_index = commands.add_parser("build-index", help="Build local BM25 and dense indexes")
    build_index.add_argument("--chunks", default="data/processed/chunks_ai.jsonl.gz")
    build_index.add_argument("--output", default="artifacts/index")
    build_index.add_argument("--cache", default="artifacts/cache")
    build_index.add_argument(
        "--embedding-model",
        default="intfloat/multilingual-e5-small",
    )
    build_index.add_argument("--batch-size", type=int, default=64)
    build_index.add_argument("--embedding-threads", type=int, default=8)
    build_index.add_argument("--max-chunks", type=int)
    build_index.set_defaults(func=_build_index)

    search = commands.add_parser("search", help="Run hybrid search from the command line")
    search.add_argument("query")
    search.add_argument("--index", default="artifacts/index")
    search.add_argument("--cache", default="artifacts/cache")
    search.add_argument("--top-k", type=int, default=8)
    search.set_defaults(func=_search)

    report = commands.add_parser("report", help="Build the data quality HTML report")
    report.add_argument("--data-quality", default="data/processed/data_quality.json")
    report.add_argument("--output", default="artifacts/reports/data_quality.html")
    report.set_defaults(func=_report)

    evaluate = commands.add_parser("evaluate", help="Evaluate BM25, dense and hybrid retrieval")
    evaluate.add_argument("--index", default="artifacts/index")
    evaluate.add_argument("--cache", default="artifacts/cache")
    evaluate.add_argument("--output", default="artifacts/reports")
    evaluate.add_argument("--queries", type=int, default=30)
    evaluate.add_argument(
        "--multilingual-queries",
        default="config/multilingual_evaluation_queries.json",
    )
    evaluate.set_defaults(func=_evaluate)

    audit = commands.add_parser(
        "audit-embedding",
        help="Verify that every evidence chunk fits the dense model context window",
    )
    audit.add_argument("--chunks", default="data/processed/chunks_ai.jsonl.gz")
    audit.add_argument(
        "--output",
        default="artifacts/reports/embedding_context_audit.json",
    )
    audit.add_argument("--tokenizer-model", default="intfloat/multilingual-e5-small")
    audit.add_argument("--token-limit", type=int, default=512)
    audit.set_defaults(func=_audit_embedding)

    verify_audit = commands.add_parser(
        "verify-audit",
        help="Verify the complete local audit event hash chain",
    )
    verify_audit.add_argument("--database", default="artifacts/audit/audit.sqlite3")
    verify_audit.set_defaults(func=_verify_audit)
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
