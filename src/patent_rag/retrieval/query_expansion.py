from __future__ import annotations

import re

HANGUL_PATTERN = re.compile(r"[가-힣]")

# Transparent, deterministic domain terms used only to add Japanese lexical recall.
# Dense retrieval always receives the user's original multilingual query.
KOREAN_JAPANESE_PATENT_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("회전 기계", ("回転機械", "回転機")),
    ("회전기계", ("回転機械", "回転機")),
    ("시작 시점", ("開始時点", "開始時期")),
    ("신경망", ("ニューラルネットワーク", "神経回路網")),
    ("뉴럴네트워크", ("ニューラルネットワーク",)),
    ("기계학습", ("機械学習",)),
    ("머신러닝", ("機械学習",)),
    ("딥러닝", ("深層学習",)),
    ("인공지능", ("人工知能",)),
    ("학습 모델", ("学習モデル",)),
    ("특징량", ("特徴量",)),
    ("시계열", ("時系列",)),
    ("레이저", ("レーザ", "レーザー")),
    ("가공", ("加工",)),
    ("조건", ("条件",)),
    ("조정", ("調整",)),
    ("최적화", ("最適化",)),
    ("사용", ("使用", "利用")),
    ("이상", ("異常",)),
    ("수명", ("寿命",)),
    ("예측", ("予測",)),
    ("영상", ("映像", "画像")),
    ("비디오", ("映像", "動画")),
    ("장면", ("シーン", "場面")),
    ("특징", ("特徴",)),
    ("추출", ("抽出",)),
    ("관련", ("関連",)),
    ("콘텐츠", ("コンテンツ",)),
    ("생성", ("生成",)),
    ("장치", ("装置",)),
    ("이미지", ("画像",)),
    ("인식", ("認識",)),
    ("분류", ("分類",)),
    ("검출", ("検出",)),
    ("센서", ("センサ",)),
    ("제어", ("制御",)),
    ("고장", ("故障",)),
    ("진단", ("診断",)),
    ("보전", ("保全",)),
    ("자연어", ("自然言語",)),
    ("검색", ("検索",)),
    ("문서", ("文書",)),
    ("데이터", ("データ",)),
    ("일본", ("日本",)),
    ("특허", ("特許",)),
    ("발명", ("発明",)),
    ("청구항", ("請求項",)),
    ("요약", ("要約",)),
)


def expand_sparse_query(query: str) -> tuple[str, list[str]]:
    """Append auditable Japanese patent terms to a Korean lexical query."""
    if not HANGUL_PATTERN.search(query):
        return query, []
    additions: list[str] = []
    for korean, japanese_terms in KOREAN_JAPANESE_PATENT_TERMS:
        if korean in query:
            additions.extend(japanese_terms)
    unique_additions = list(dict.fromkeys(additions))
    if not unique_additions:
        return query, []
    return f"{query} {' '.join(unique_additions)}", unique_additions
