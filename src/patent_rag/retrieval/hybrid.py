from __future__ import annotations

import gzip
import hashlib
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from patent_rag.retrieval.bm25 import BM25Index, RankedItem
from patent_rag.retrieval.dense import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_INFERENCE_THREADS,
    DenseIndex,
)
from patent_rag.retrieval.query_expansion import expand_sparse_query


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SearchHit:
    rank: int
    score: float
    sparse_score: float | None
    dense_score: float | None
    chunk: dict[str, Any]


def reciprocal_rank_fusion(
    rankings: list[list[RankedItem]],
    *,
    rank_constant: int = 60,
) -> list[tuple[int, float]]:
    scores: defaultdict[int, float] = defaultdict(float)
    for ranking in rankings:
        for item in ranking:
            scores[item.index] += 1.0 / (rank_constant + item.rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


class HybridRetriever:
    def __init__(
        self,
        chunks: list[dict[str, Any]],
        bm25: BM25Index,
        dense: DenseIndex,
    ) -> None:
        if not (len(chunks) == bm25.matrix.shape[0] == dense.embeddings.shape[0]):
            raise ValueError("Chunk metadata and index row counts do not match")
        self.chunks = chunks
        self.bm25 = bm25
        self.dense = dense

    @classmethod
    def load(cls, index_dir: Path, cache_dir: Path | None = None) -> HybridRetriever:
        manifest = json.loads((index_dir / "index_manifest.json").read_text(encoding="utf-8"))
        chunks = [
            json.loads(line)
            for line in (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        return cls(
            chunks,
            BM25Index.load(index_dir),
            DenseIndex.load(
                index_dir,
                model_name=manifest["embedding_model"],
                cache_dir=cache_dir,
            ),
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        candidate_k: int = 40,
        years: set[int] | None = None,
        sections: set[str] | None = None,
    ) -> list[SearchHit]:
        allowed = np.ones(len(self.chunks), dtype=bool)
        if years:
            allowed &= np.asarray([int(chunk["year"]) in years for chunk in self.chunks])
        if sections:
            allowed &= np.asarray(
                [
                    str(chunk["section"]) in sections
                    or ("claims" in sections and str(chunk["section"]).startswith("claim_"))
                    for chunk in self.chunks
                ]
            )

        sparse_query, _ = expand_sparse_query(query)
        sparse_ranking = self.bm25.search(sparse_query, candidate_k, allowed)
        dense_ranking = self.dense.search(query, candidate_k, allowed)
        sparse_scores = {item.index: item.score for item in sparse_ranking}
        dense_scores = {item.index: item.score for item in dense_ranking}
        fused_candidates = reciprocal_rank_fusion([sparse_ranking, dense_ranking])
        document_counts: Counter[str] = Counter()
        fused: list[tuple[int, float]] = []
        for index, score in fused_candidates:
            document_id = str(self.chunks[index]["document_id"])
            if document_counts[document_id] >= 2:
                continue
            document_counts[document_id] += 1
            fused.append((index, score))
            if len(fused) == top_k:
                break
        return [
            SearchHit(
                rank=rank,
                score=score,
                sparse_score=sparse_scores.get(index),
                dense_score=dense_scores.get(index),
                chunk=self.chunks[index],
            )
            for rank, (index, score) in enumerate(fused, 1)
        ]


def build_hybrid_index(
    chunks_path: Path,
    index_dir: Path,
    *,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path | None = None,
    max_chunks: int | None = None,
    batch_size: int = 64,
    embedding_threads: int = DEFAULT_INFERENCE_THREADS,
) -> dict[str, Any]:
    build_started = time.perf_counter()
    index_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, Any]] = []
    with gzip.open(chunks_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            chunks.append(json.loads(line))
            if max_chunks is not None and len(chunks) >= max_chunks:
                break
    if not chunks:
        raise ValueError(f"No chunks found in {chunks_path}")

    texts = [str(chunk["text"]) for chunk in chunks]
    bm25_started = time.perf_counter()
    bm25 = BM25Index.build(texts)
    bm25.save(index_dir)
    bm25_seconds = time.perf_counter() - bm25_started
    dense_started = time.perf_counter()
    dense = DenseIndex.build(
        texts,
        embedding_model,
        cache_dir=cache_dir,
        batch_size=batch_size,
        threads=embedding_threads,
    )
    dense.save(index_dir)
    dense_seconds = time.perf_counter() - dense_started

    with (index_dir / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False, separators=(",", ":")) + "\n")

    years = sorted({int(chunk["year"]) for chunk in chunks})
    documents = {str(chunk["document_id"]) for chunk in chunks}
    manifest: dict[str, Any] = {
        "index_version": "0.1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "chunks": len(chunks),
        "documents": len(documents),
        "years": years,
        "embedding_model": embedding_model,
        "embedding_dimensions": int(dense.embeddings.shape[1]),
        "embedding_input_prefixes": (
            {"query": "query: ", "passage": "passage: "}
            if embedding_model == DEFAULT_EMBEDDING_MODEL
            else None
        ),
        "sparse_method": "BM25(k1=1.5,b=0.75)+SudachiPy(C)",
        "dense_method": "cosine similarity",
        "embedding_batch_size": batch_size,
        "embedding_threads": embedding_threads,
        "fusion_method": "RRF(k=60)",
        "query_expansion": "deterministic Korean-to-Japanese patent terminology v1 (sparse only)",
        "source_chunks": str(chunks_path.as_posix()),
        "source_chunks_sha256": _sha256(chunks_path),
        "build_seconds": round(time.perf_counter() - build_started, 3),
        "phase_seconds": {
            "bm25": round(bm25_seconds, 3),
            "dense": round(dense_seconds, 3),
        },
        "artifact_sha256": {
            "bm25_matrix.npz": _sha256(index_dir / "bm25_matrix.npz"),
            "bm25_vectorizer.joblib": _sha256(index_dir / "bm25_vectorizer.joblib"),
            "dense_embeddings.npy": _sha256(index_dir / "dense_embeddings.npy"),
            "chunks.jsonl": _sha256(index_dir / "chunks.jsonl"),
        },
    }
    (index_dir / "index_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
