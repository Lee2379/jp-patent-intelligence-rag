from patent_rag.parsing.japanese_patent import parse_patent
from patent_rag.pipeline.chunking import chunk_document, split_japanese_text

SAMPLE = """(57)【要約】【課題】学習モデルの精度を改善する。【解決手段】機械学習を用いる。
【特許請求の範囲】
【請求項１】ニューラルネットワークを用いる情報処理装置。
【請求項２】請求項1に記載の情報処理装置。
【発明の詳細な説明】
【技術分野】【０００１】本発明は人工知能に関する。
【背景技術】【０００２】従来技術には課題があった。
【発明が解決しようとする課題】【０００３】検索精度を高める。
"""


def test_parse_sections_and_identity() -> None:
    document = parse_patent(
        SAMPLE,
        "dataset/2020/A/2020151001/2020151725.xml.html.txt",
    )
    assert document.document_id == "2020151725"
    assert document.year == 2020
    assert document.publication_kind == "A"
    assert len(document.claims) == 2
    assert document.ai_score >= 5
    assert {section.name for section in document.sections} >= {"技術分野", "背景技術"}


def test_chunk_ids_are_stable() -> None:
    document = parse_patent(SAMPLE, "dataset/2020/A/2020151725.xml.html.txt")
    first = [chunk.chunk_id for chunk in chunk_document(document)]
    second = [chunk.chunk_id for chunk in chunk_document(document)]
    assert first == second
    assert len(first) >= 5


def test_long_japanese_text_is_bounded() -> None:
    chunks = split_japanese_text("文です。" * 500, max_chars=120, overlap_chars=20)
    assert len(chunks) > 1
    assert max(map(len, chunks)) <= 120


def test_sentence_overlap_never_breaks_character_cap() -> None:
    text = f"{'技術' * 40}。{'装置' * 40}。"
    chunks = split_japanese_text(text, max_chars=100, overlap_chars=30)
    assert max(map(len, chunks)) <= 100


def test_long_abstract_without_claim_marker_parses_linearly() -> None:
    document = parse_patent(
        "【要約】" + ("長い特許本文です。" * 20_000),
        "dataset/2020/A/2020999999.xml.html.txt",
    )
    assert document.document_id == "2020999999"
    assert document.abstract.startswith("長い特許本文")
