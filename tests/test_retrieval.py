import numpy as np

from patent_rag.retrieval.bm25 import BM25Index, RankedItem
from patent_rag.retrieval.dense import E5_SMALL_MODEL, _passage_texts, _query_text
from patent_rag.retrieval.hybrid import reciprocal_rank_fusion


def test_bm25_ranks_relevant_japanese_document_first() -> None:
    documents = [
        "ニューラルネットワークを用いた画像分類装置",
        "配送車両の経路を案内する地図表示装置",
        "機械学習モデルによる画像の分類方法",
    ]
    index = BM25Index.build(documents)
    hits = index.search("機械学習で画像分類", top_k=3)
    assert hits
    assert hits[0].index in {0, 2}
    assert all(np.isfinite(hit.score) for hit in hits)


def test_rrf_rewards_agreement_between_retrievers() -> None:
    sparse = [RankedItem(0, 9.0, 1), RankedItem(1, 4.0, 2)]
    dense = [RankedItem(2, 0.9, 1), RankedItem(0, 0.8, 2)]
    fused = reciprocal_rank_fusion([sparse, dense])
    assert fused[0][0] == 0


def test_e5_uses_asymmetric_retrieval_prefixes() -> None:
    assert _query_text("機械学習", E5_SMALL_MODEL) == "query: 機械学習"
    assert list(_passage_texts(["特許文献"], E5_SMALL_MODEL)) == ["passage: 特許文献"]


def test_non_e5_model_does_not_receive_e5_prefixes() -> None:
    model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert _query_text("機械学習", model) == "機械学習"
    assert list(_passage_texts(["特許文献"], model)) == ["特許文献"]
