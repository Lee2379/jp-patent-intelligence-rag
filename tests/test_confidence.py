from patent_rag.retrieval.confidence import assess_evidence, select_generation_hits
from patent_rag.retrieval.hybrid import SearchHit


def _hit(document_id: str, dense_score: float | None) -> SearchHit:
    return SearchHit(
        rank=1,
        score=0.02,
        sparse_score=10.0,
        dense_score=dense_score,
        chunk={"document_id": document_id},
    )


def test_evidence_gate_accepts_technical_query_above_threshold() -> None:
    result = assess_evidence(
        "기계학습 레이저 가공 특허",
        [_hit("2020151725", 0.84)],
        min_dense_score=0.81,
    )
    assert result.accepted is True
    assert result.reason == "technical_cue_and_dense_similarity_passed"


def test_evidence_gate_rejects_out_of_domain_query_even_with_dense_hit() -> None:
    result = assess_evidence(
        "오키나와 해변과 파스타 식당 추천",
        [_hit("2004157779", 0.84)],
        min_dense_score=0.81,
    )
    assert result.accepted is False
    assert result.reason == "no_supported_technical_domain_cue"


def test_evidence_gate_accepts_exact_retrieved_document_id() -> None:
    result = assess_evidence(
        "JP2020151725 내용을 요약해줘",
        [_hit("2020151725", 0.70)],
        min_dense_score=0.81,
    )
    assert result.accepted is True
    assert result.reason == "exact_document_id_match"


def test_generation_pack_keeps_coherent_top_hits_and_minimum_context() -> None:
    hits = [
        SearchHit(
            rank=index,
            score=score,
            sparse_score=10.0,
            dense_score=0.85,
            chunk={"document_id": str(index)},
        )
        for index, score in enumerate([0.032, 0.031, 0.020, 0.015], 1)
    ]
    selected = select_generation_hits("機械学習の課題", hits)
    assert [hit.rank for hit in selected] == [1, 2]


def test_generation_pack_focuses_on_repeated_top_document() -> None:
    hits = [
        SearchHit(1, 0.032, 10.0, 0.90, {"document_id": "A"}),
        SearchHit(2, 0.030, 9.0, 0.89, {"document_id": "A"}),
        SearchHit(3, 0.029, 8.0, 0.88, {"document_id": "B"}),
    ]
    selected = select_generation_hits("課題と解決手段を比較", hits)
    assert [hit.chunk["document_id"] for hit in selected] == ["A", "A"]
