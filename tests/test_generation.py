import json

from patent_rag.generation.ollama import render_structured_answer, validate_citations
from patent_rag.retrieval.hybrid import SearchHit


def test_citation_validator_accepts_only_supplied_source_ids() -> None:
    citations, grounded = validate_citations("根拠があります。[S1] 比較できます。[S3]", 3)
    assert citations == ["S1", "S3"]
    assert grounded is True


def test_citation_validator_rejects_missing_or_unknown_ids() -> None:
    assert validate_citations("引用がありません。", 3)[1] is False
    assert validate_citations("存在しない出典です。[S4]", 3)[1] is False


def test_citation_validator_supports_non_contiguous_source_ids() -> None:
    assert validate_citations("根拠。[S1] 補足。[S3]", {1, 3})[1] is True
    assert validate_citations("許可されない根拠。[S2]", {1, 3})[1] is False


def test_structured_answer_renders_only_allowed_source_ids() -> None:
    hits = [
        SearchHit(
            rank=1,
            score=0.03,
            sparse_score=10.0,
            dense_score=0.9,
            chunk={"document_id": "2020151725", "section": "abstract"},
        )
    ]
    raw = json.dumps(
        {
            "problem": {"text": "課題", "source_ids": ["S1"]},
            "solution": {"text": "解決", "source_ids": ["S1"]},
        },
        ensure_ascii=False,
    )
    rendered = render_structured_answer(raw, hits, "ja")
    assert rendered is not None
    assert rendered[1] == ["S1"]
    assert "根拠の限界" in rendered[0]


def test_structured_answer_rejects_unknown_source_id() -> None:
    hits = [SearchHit(1, 0.03, 10.0, 0.9, {"document_id": "1", "section": "abstract"})]
    raw = json.dumps({key: {"text": key, "source_ids": ["S9"]} for key in ("problem", "solution")})
    assert render_structured_answer(raw, hits, "ja") is None
