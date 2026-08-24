from patent_rag.retrieval.query_expansion import expand_sparse_query


def test_korean_patent_terms_are_expanded_for_sparse_recall() -> None:
    expanded, terms = expand_sparse_query("기계학습을 사용해 레이저 가공 조건을 조정하는 일본 특허")
    assert expanded.startswith("기계학습을 사용해")
    assert {"機械学習", "レーザ", "加工", "条件", "調整", "日本", "特許"} <= set(terms)


def test_non_korean_query_is_not_modified() -> None:
    query = "機械学習を用いたレーザ加工"
    assert expand_sparse_query(query) == (query, [])
