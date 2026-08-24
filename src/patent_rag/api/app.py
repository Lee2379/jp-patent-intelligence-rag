from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from patent_rag.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    HealthResponse,
    ReviewRequest,
    ReviewResponse,
    SearchRequest,
    SearchResponse,
    SourceResponse,
)
from patent_rag.audit import AuditStore
from patent_rag.generation.ollama import PROMPT_TEMPLATE_VERSION, OllamaGenerator
from patent_rag.retrieval.confidence import assess_evidence, select_generation_hits
from patent_rag.retrieval.hybrid import HybridRetriever, SearchHit
from patent_rag.settings import Settings, get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEB_DIR = PROJECT_ROOT / "apps" / "web"


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.retriever: HybridRetriever | None = None
        self.index_manifest: dict[str, Any] = {}
        self.load_error: str | None = None
        self.generator = OllamaGenerator(
            settings.ollama_base_url,
            settings.ollama_model,
            settings.ollama_timeout_seconds,
        )
        self.audit = AuditStore(settings.patent_rag_audit_db)

    def load(self) -> None:
        try:
            self.retriever = HybridRetriever.load(
                self.settings.patent_rag_index_dir,
                cache_dir=self.settings.patent_rag_cache_dir,
            )
            manifest_path = self.settings.patent_rag_index_dir / "index_manifest.json"
            self.index_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.load_error = None
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
            self.load_error = str(error)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    runtime = Runtime(get_settings())
    runtime.load()
    app.state.runtime = runtime
    yield


app = FastAPI(
    title="JP Patent Intelligence RAG",
    version="0.1.0",
    description="Fully local hybrid RAG over Japanese AI patent evidence.",
    lifespan=lifespan,
)


def _runtime(request: Request) -> Runtime:
    return cast(Runtime, request.app.state.runtime)


def _require_retriever(runtime: Runtime) -> HybridRetriever:
    if runtime.retriever is None:
        raise HTTPException(
            status_code=503,
            detail=f"Index is not ready. Run `patent-rag build-index`. {runtime.load_error or ''}",
        )
    return runtime.retriever


def _require_valid_audit(runtime: Runtime) -> None:
    verification = runtime.audit.verify_chain()
    if not verification["valid"]:
        raise HTTPException(
            status_code=503,
            detail="Audit chain validation failed; generation and review are disabled.",
        )


def _source(hit: SearchHit, index: int) -> SourceResponse:
    chunk = hit.chunk
    return SourceResponse(
        source_id=f"S{index}",
        rank=hit.rank,
        score=round(hit.score, 8),
        sparse_score=round(hit.sparse_score, 6) if hit.sparse_score is not None else None,
        dense_score=round(hit.dense_score, 6) if hit.dense_score is not None else None,
        document_id=str(chunk["document_id"]),
        year=int(chunk["year"]),
        publication_kind=str(chunk["publication_kind"]),
        section=str(chunk["section"]),
        text=str(chunk["text"]),
        local_path=str(chunk["local_path"]),
    )


def _retrieve(retriever: HybridRetriever, payload: SearchRequest) -> tuple[list[SearchHit], float]:
    started = time.perf_counter()
    hits = retriever.search(
        payload.query,
        top_k=payload.top_k,
        years=set(payload.years) if payload.years else None,
        sections=set(payload.sections) if payload.sections else None,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return hits, elapsed_ms


@app.get("/api/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    runtime = _runtime(request)
    ollama = await runtime.generator.health()
    retrieval_ready = runtime.retriever is not None
    audit_verification = runtime.audit.verify_chain()
    status: Literal["ready", "degraded", "starting"] = (
        "ready"
        if retrieval_ready and ollama["model_ready"] and audit_verification["valid"]
        else "degraded"
        if retrieval_ready
        else "starting"
    )
    return HealthResponse(
        status=status,
        retrieval_ready=retrieval_ready,
        ollama=ollama,
        audit={
            "ready": True,
            "chain_valid": audit_verification["valid"],
            "events": audit_verification["events_checked"],
        },
    )


@app.get("/api/stats")
async def stats(request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    data_quality_path = runtime.settings.patent_rag_data_dir / "data_quality.json"
    data_quality = (
        json.loads(data_quality_path.read_text(encoding="utf-8"))
        if data_quality_path.exists()
        else {}
    )
    return {
        "project": "JP Patent Intelligence RAG",
        "local_only": True,
        "required_cost_usd": 0,
        "index": runtime.index_manifest,
        "data": data_quality,
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(payload: SearchRequest, request: Request) -> SearchResponse:
    runtime = _runtime(request)
    _require_valid_audit(runtime)
    retriever = _require_retriever(runtime)
    hits, retrieval_ms = _retrieve(retriever, payload)
    sources = [_source(hit, index) for index, hit in enumerate(hits, 1)]
    receipt = runtime.audit.append_event(
        "search_performed",
        payload.actor_id,
        {
            "session_id": payload.session_id,
            "query": payload.query,
            "filters": {"years": payload.years, "sections": payload.sections},
            "top_k": payload.top_k,
            "retrieval_ms": round(retrieval_ms, 2),
            "index_manifest": runtime.index_manifest,
            "sources": [source.model_dump() for source in sources],
        },
    )
    return SearchResponse(
        query=payload.query,
        retrieval_ms=round(retrieval_ms, 2),
        results=sources,
        audit_id=receipt.event_id,
        audit_hash=receipt.event_hash,
    )


@app.post("/api/answer", response_model=AnswerResponse)
async def answer(payload: AnswerRequest, request: Request) -> AnswerResponse:
    runtime = _runtime(request)
    _require_valid_audit(runtime)
    retriever = _require_retriever(runtime)
    total_started = time.perf_counter()
    hits, retrieval_ms = _retrieve(retriever, payload)
    evidence_assessment = assess_evidence(
        payload.query,
        hits,
        min_dense_score=runtime.settings.patent_rag_min_dense_score,
    )
    generation_hits = (
        select_generation_hits(payload.query, hits) if evidence_assessment.accepted else []
    )
    generation_started = time.perf_counter()
    generated = await runtime.generator.generate(
        payload.query,
        generation_hits,
        payload.answer_language,
    )
    generation_ms = (time.perf_counter() - generation_started) * 1000
    total_ms = (time.perf_counter() - total_started) * 1000
    sources = [_source(hit, index) for index, hit in enumerate(hits, 1)]
    review_status: Literal["pending", "not_required"] = (
        "pending" if payload.require_review else "not_required"
    )
    receipt = runtime.audit.append_event(
        "answer_generated",
        payload.actor_id,
        {
            "session_id": payload.session_id,
            "query": payload.query,
            "filters": {"years": payload.years, "sections": payload.sections},
            "top_k": payload.top_k,
            "answer_language": payload.answer_language,
            "answer": generated.text,
            "raw_model_output": generated.raw_model_output,
            "grounded": generated.grounded,
            "citation_validation_passed": generated.citation_validation_passed,
            "mode": generated.mode,
            "model": generated.model,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "evidence_assessment": asdict(evidence_assessment),
            "generation_evidence": [
                {
                    "source_id": f"S{hit.rank}",
                    "document_id": str(hit.chunk["document_id"]),
                    "section": str(hit.chunk["section"]),
                    "rrf_score": hit.score,
                }
                for hit in generation_hits
            ],
            "model_input": {
                "system_prompt": generated.system_prompt,
                "user_prompt": generated.user_prompt,
                "generation_options": generated.generation_options,
            },
            "index_manifest": runtime.index_manifest,
            "cited_source_ids": generated.cited_source_ids,
            "timings_ms": {
                "retrieval": round(retrieval_ms, 2),
                "generation": round(generation_ms, 2),
                "total": round(total_ms, 2),
            },
            "sources": [source.model_dump() for source in sources],
            "review_required": payload.require_review,
            "initial_review_status": review_status,
        },
    )
    return AnswerResponse(
        query=payload.query,
        answer=generated.text,
        grounded=generated.grounded,
        mode=generated.mode,
        model=generated.model,
        cited_source_ids=generated.cited_source_ids,
        retrieval_ms=round(retrieval_ms, 2),
        generation_ms=round(generation_ms, 2),
        total_ms=round(total_ms, 2),
        sources=sources,
        evidence_assessment=asdict(evidence_assessment),
        disclaimer=(
            "AI生成の技術検索draftです。Human review承認前の運用利用を想定していません。"
            "特許性・侵害・法的状態に関する法的助言ではありません。"
        ),
        audit_id=receipt.event_id,
        audit_hash=receipt.event_hash,
        review_status=review_status,
    )


@app.post("/api/review", response_model=ReviewResponse)
async def review(payload: ReviewRequest, request: Request) -> ReviewResponse:
    runtime = _runtime(request)
    _require_valid_audit(runtime)
    try:
        receipt = runtime.audit.record_review(
            payload.answer_audit_id,
            payload.reviewer_id,
            payload.decision,
            payload.notes,
        )
    except ValueError as error:
        status_code = 409 if "must differ" in str(error) else 404
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    verification = runtime.audit.verify_chain()
    return ReviewResponse(
        answer_audit_id=payload.answer_audit_id,
        review_audit_id=receipt.event_id,
        review_audit_hash=receipt.event_hash,
        review_status=payload.decision,
        chain_valid=bool(verification["valid"]),
    )


@app.get("/api/audit/events")
async def audit_events(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    runtime = _runtime(request)
    events = runtime.audit.list_events(limit)
    return {"events": events, "count": len(events)}


@app.get("/api/audit/events/{event_id}")
async def audit_event(event_id: str, request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    event = runtime.audit.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    if event["event_type"] == "answer_generated":
        event["review_status"] = runtime.audit.latest_review_status(event_id)
    return event


@app.get("/api/audit/verify")
async def audit_verify(request: Request) -> dict[str, Any]:
    return _runtime(request).audit.verify_chain()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/audit")
async def audit_console() -> FileResponse:
    return FileResponse(WEB_DIR / "audit.html")


app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")
