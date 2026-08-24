from __future__ import annotations

import os
import warnings
from collections.abc import Iterable
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType
from tqdm.auto import tqdm

from patent_rag.retrieval.bm25 import RankedItem

DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
E5_SMALL_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_INFERENCE_THREADS = max(1, min(os.cpu_count() or 1, 8))


def _register_custom_models() -> None:
    supported = {str(item["model"]) for item in TextEmbedding.list_supported_models()}
    if E5_SMALL_MODEL in supported:
        return
    TextEmbedding.add_custom_model(
        model=E5_SMALL_MODEL,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf=E5_SMALL_MODEL),
        dim=384,
        model_file="onnx/model.onnx",
        description=(
            "Multilingual E5-small, 94 languages, 512-token context; "
            "query/passage prefixes required."
        ),
        license="MIT",
        size_in_gb=0.47,
    )


def _passage_texts(texts: Iterable[str], model_name: str) -> Iterable[str]:
    if model_name == E5_SMALL_MODEL:
        return (f"passage: {text}" for text in texts)
    return texts


def _query_text(query: str, model_name: str) -> str:
    return f"query: {query}" if model_name == E5_SMALL_MODEL else query


class DenseIndex:
    def __init__(
        self,
        embeddings: np.ndarray,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: Path | None = None,
        threads: int = DEFAULT_INFERENCE_THREADS,
    ) -> None:
        self.embeddings = embeddings.astype(np.float32, copy=False)
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads
        self._model: TextEmbedding | None = None

    @property
    def model(self) -> TextEmbedding:
        if self._model is None:
            _register_custom_models()
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"The model .* now uses mean pooling instead of CLS embedding.*",
                )
                if self.cache_dir is not None:
                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        cache_dir=str(self.cache_dir),
                        threads=self.threads,
                    )
                else:
                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        threads=self.threads,
                    )
        return self._model

    @classmethod
    def build(
        cls,
        texts: list[str],
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: Path | None = None,
        batch_size: int = 128,
        threads: int = DEFAULT_INFERENCE_THREADS,
    ) -> DenseIndex:
        empty = np.empty((0, 384), dtype=np.float32)
        index = cls(
            empty,
            model_name=model_name,
            cache_dir=cache_dir,
            threads=threads,
        )
        vector_stream = index.model.embed(
            _passage_texts(texts, model_name),
            batch_size=batch_size,
            parallel=None,
        )
        vectors = list(tqdm(vector_stream, total=len(texts), desc="Embedding patent chunks"))
        embeddings = np.asarray(vectors, dtype=np.float32)
        embeddings /= np.maximum(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12)
        index.embeddings = embeddings
        return index

    def search(
        self,
        query: str,
        top_k: int = 40,
        allowed_mask: np.ndarray | None = None,
    ) -> list[RankedItem]:
        query_embedding = np.asarray(
            next(iter(self.model.query_embed(_query_text(query, self.model_name)))),
            dtype=np.float32,
        )
        query_embedding /= max(float(np.linalg.norm(query_embedding)), 1e-12)
        scores = self.embeddings @ query_embedding
        if allowed_mask is not None:
            scores = np.where(allowed_mask, scores, -np.inf)
        finite = np.isfinite(scores)
        count = min(top_k, int(np.count_nonzero(finite)))
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
        np.save(directory / "dense_embeddings.npy", self.embeddings, allow_pickle=False)

    @classmethod
    def load(
        cls,
        directory: Path,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: Path | None = None,
        threads: int = DEFAULT_INFERENCE_THREADS,
    ) -> DenseIndex:
        embeddings = np.load(directory / "dense_embeddings.npy", mmap_mode="r")
        return cls(
            embeddings,
            model_name=model_name,
            cache_dir=cache_dir,
            threads=threads,
        )
