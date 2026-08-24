from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=4, ge=1, le=20)
    years: list[int] | None = None
    sections: list[str] | None = None
    actor_id: str = Field(default="analyst-01", min_length=2, max_length=64)
    session_id: str | None = Field(default=None, max_length=128)


class AnswerRequest(SearchRequest):
    answer_language: Literal["ja", "ko", "en"] = "ja"
    require_review: bool = True


class ReviewRequest(BaseModel):
    answer_audit_id: str = Field(min_length=36, max_length=36)
    reviewer_id: str = Field(min_length=2, max_length=64)
    decision: Literal["approved", "needs_revision", "rejected"]
    notes: str = Field(default="", max_length=1000)


class SourceResponse(BaseModel):
    source_id: str
    rank: int
    score: float
    sparse_score: float | None
    dense_score: float | None
    document_id: str
    year: int
    publication_kind: str
    section: str
    text: str
    local_path: str


class SearchResponse(BaseModel):
    query: str
    retrieval_ms: float
    results: list[SourceResponse]
    audit_id: str
    audit_hash: str


class AnswerResponse(BaseModel):
    query: str
    answer: str
    grounded: bool
    mode: str
    model: str
    cited_source_ids: list[str]
    retrieval_ms: float
    generation_ms: float
    total_ms: float
    sources: list[SourceResponse]
    evidence_assessment: dict[str, Any]
    disclaimer: str
    audit_id: str
    audit_hash: str
    review_status: Literal["not_required", "pending", "approved", "needs_revision", "rejected"]


class ReviewResponse(BaseModel):
    answer_audit_id: str
    review_audit_id: str
    review_audit_hash: str
    review_status: Literal["approved", "needs_revision", "rejected"]
    chain_valid: bool


class HealthResponse(BaseModel):
    status: Literal["ready", "degraded", "starting"]
    retrieval_ready: bool
    ollama: dict[str, Any]
    audit: dict[str, Any]
    cost_mode: str = "$0 local-only"
