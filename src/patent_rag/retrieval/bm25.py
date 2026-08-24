from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer

from patent_rag.retrieval.tokenization import sudachi_tokenize


@dataclass(frozen=True, slots=True)
class RankedItem:
    index: int
    score: float
    rank: int


class BM25Index:
    """Sparse BM25 stored as a SciPy CSR matrix for transparent, fast local search."""

    def __init__(self, vectorizer: CountVectorizer, matrix: sparse.csr_matrix) -> None:
        self.vectorizer = vectorizer
        self.matrix = matrix

    @classmethod
    def build(
        cls,
        texts: list[str],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> BM25Index:
        if not texts:
            raise ValueError("Cannot build BM25 index from an empty corpus")
        vectorizer = CountVectorizer(
            tokenizer=sudachi_tokenize,
            token_pattern=None,
            lowercase=False,
            dtype=np.float32,
            min_df=1,
        )
        counts = vectorizer.fit_transform(texts).tocsr()
        document_lengths = np.asarray(counts.sum(axis=1)).ravel()
        average_length = max(float(document_lengths.mean()), 1.0)
        document_frequency = np.asarray((counts > 0).sum(axis=0)).ravel()
        document_count = counts.shape[0]
        idf = np.log1p((document_count - document_frequency + 0.5) / (document_frequency + 0.5))

        row_ids = np.repeat(np.arange(document_count), np.diff(counts.indptr))
        term_frequency = counts.data.astype(np.float32, copy=True)
        length_norm = k1 * (1.0 - b + b * document_lengths[row_ids] / average_length)
        weights = (
            idf[counts.indices] * term_frequency * (k1 + 1.0) / (term_frequency + length_norm)
        ).astype(np.float32)
        matrix = sparse.csr_matrix(
            (weights, counts.indices.copy(), counts.indptr.copy()),
            shape=counts.shape,
        )
        return cls(vectorizer, matrix)

    def search(
        self,
        query: str,
        top_k: int = 40,
        allowed_mask: np.ndarray | None = None,
    ) -> list[RankedItem]:
        query_vector = self.vectorizer.transform([query])
        term_indices = np.unique(query_vector.indices)
        if term_indices.size == 0:
            return []
        scores = np.asarray(self.matrix[:, term_indices].sum(axis=1)).ravel()
        if allowed_mask is not None:
            scores = np.where(allowed_mask, scores, -np.inf)
        valid_count = int(np.count_nonzero(np.isfinite(scores) & (scores > 0)))
        count = min(top_k, valid_count)
        if count == 0:
            return []
        candidate_indices = np.argpartition(scores, -count)[-count:]
        ordered = candidate_indices[np.argsort(scores[candidate_indices])[::-1]]
        return [
            RankedItem(index=int(item), score=float(scores[item]), rank=rank)
            for rank, item in enumerate(ordered, 1)
        ]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, directory / "bm25_vectorizer.joblib")
        sparse.save_npz(directory / "bm25_matrix.npz", self.matrix, compressed=True)

    @classmethod
    def load(cls, directory: Path) -> BM25Index:
        vectorizer = joblib.load(directory / "bm25_vectorizer.joblib")
        matrix = sparse.load_npz(directory / "bm25_matrix.npz").tocsr()
        return cls(vectorizer, matrix)
