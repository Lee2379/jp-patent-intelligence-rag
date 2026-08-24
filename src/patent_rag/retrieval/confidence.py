from __future__ import annotations

import re
from dataclasses import dataclass

from patent_rag.retrieval.hybrid import SearchHit

DOCUMENT_ID_PATTERN = re.compile(r"(?:JP\s*)?(\d{10})", flags=re.IGNORECASE)
DOMAIN_CUES = (
    # Japanese
    "機械学習",
    "深層学習",
    "ニューラル",
    "人工知能",
    "学習モデル",
    "特徴量",
    "時系列",
    "予測",
    "認識",
    "分類",
    "検出",
    "最適化",
    "制御",
    "異常",
    "診断",
    "画像",
    "映像",
    "自然言語",
    "検索",
    "特許",
    "発明",
    "請求項",
    "レーザ",
    "加工",
    "回転機",
    # Korean
    "기계학습",
    "머신러닝",
    "딥러닝",
    "인공지능",
    "신경망",
    "뉴럴",
    "학습 모델",
    "특징량",
    "시계열",
    "예측",
    "인식",
    "분류",
    "검출",
    "최적화",
    "제어",
    "이상",
    "진단",
    "이미지",
    "영상",
    "자연어",
    "검색",
    "특허",
    "발명",
    "청구항",
    "레이저",
    "가공",
    "회전 기계",
    # English
    "machine learning",
    "deep learning",
    "neural",
    "artificial intelligence",
    "feature",
    "time series",
    "predict",
    "recogn",
    "classif",
    "detect",
    "optimiz",
    "control",
    "anomal",
    "diagnos",
    "image",
    "video",
    "natural language",
    "retriev",
    "patent",
    "invention",
    "claim",
    "laser",
    "processing",
    "device",
)
MULTI_DOCUMENT_COMPARISON_CUES = (
    "複数の特許",
    "特許同士",
    "文献を比較",
    "発明を比較",
    "특허들을 비교",
    "특허 간 비교",
    "여러 특허",
    "compare patents",
    "compare inventions",
    "multiple patents",
)


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    accepted: bool
    reason: str
    strongest_dense_score: float | None
    matched_domain_cues: list[str]
    matched_document_id: str | None
    threshold: float


def assess_evidence(
    query: str,
    hits: list[SearchHit],
    *,
    min_dense_score: float,
) -> EvidenceAssessment:
    """Apply a conservative, auditable generation gate to retrieved evidence."""
    normalized = query.casefold()
    cues = [cue for cue in DOMAIN_CUES if cue.casefold() in normalized]
    dense_scores = [hit.dense_score for hit in hits if hit.dense_score is not None]
    strongest_dense = max(dense_scores) if dense_scores else None
    match = DOCUMENT_ID_PATTERN.search(query)
    requested_document = match.group(1) if match else None
    exact_match = requested_document and any(
        str(hit.chunk["document_id"]) == requested_document for hit in hits
    )

    if not hits:
        reason = "no_retrieved_evidence"
        accepted = False
    elif exact_match:
        reason = "exact_document_id_match"
        accepted = True
    elif not cues:
        reason = "no_supported_technical_domain_cue"
        accepted = False
    elif strongest_dense is None or strongest_dense < min_dense_score:
        reason = "dense_similarity_below_calibrated_threshold"
        accepted = False
    else:
        reason = "technical_cue_and_dense_similarity_passed"
        accepted = True

    return EvidenceAssessment(
        accepted=accepted,
        reason=reason,
        strongest_dense_score=strongest_dense,
        matched_domain_cues=cues,
        matched_document_id=requested_document if exact_match else None,
        threshold=min_dense_score,
    )


def select_generation_hits(
    query: str,
    hits: list[SearchHit],
    *,
    min_relative_rrf: float = 0.75,
    min_hits: int = 2,
) -> list[SearchHit]:
    """Keep a compact, coherent evidence pack while preserving a minimum context set."""
    if not hits:
        return []
    normalized = query.casefold()
    requests_multiple_documents = any(
        cue.casefold() in normalized for cue in MULTI_DOCUMENT_COMPARISON_CUES
    )
    top_document_id = str(hits[0].chunk["document_id"])
    top_document_hits = [hit for hit in hits if str(hit.chunk["document_id"]) == top_document_id]
    if not requests_multiple_documents and len(top_document_hits) >= 2:
        return top_document_hits[:3]
    cutoff = hits[0].score * min_relative_rrf
    selected = [hit for hit in hits if hit.score >= cutoff]
    selected_count = min(len(hits), max(len(selected), min_hits))
    return hits[:selected_count]
