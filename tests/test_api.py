import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import patent_rag.api.app as api_module
from patent_rag.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        patent_rag_data_dir=tmp_path / "data",
        patent_rag_index_dir=tmp_path / "missing-index",
        patent_rag_cache_dir=tmp_path / "cache",
        patent_rag_audit_db=tmp_path / "audit" / "audit.sqlite3",
        ollama_base_url="http://127.0.0.1:1",
    )


def test_root_serves_offline_analyst_ui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "get_settings", lambda: _settings(tmp_path))
    with TestClient(api_module.app) as client:
        response = client.get("/")
        audit_response = client.get("/audit")
    assert response.status_code == 200
    assert "$0 · LOCAL ONLY" in response.text
    assert audit_response.status_code == 200
    assert "Every question" in audit_response.text


def test_answer_fails_closed_when_index_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_module, "get_settings", lambda: _settings(tmp_path))
    with TestClient(api_module.app) as client:
        response = client.post(
            "/api/answer",
            json={"query": "機械学習を用いた画像認識", "answer_language": "ja"},
        )
    assert response.status_code == 503
    assert "Index is not ready" in response.json()["detail"]


def test_human_review_endpoint_records_decision_and_valid_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_module, "get_settings", lambda: _settings(tmp_path))
    with TestClient(api_module.app) as client:
        answer = client.app.state.runtime.audit.append_event(
            "answer_generated",
            "analyst-a",
            {"query": "機械学習", "answer": "draft"},
        )
        response = client.post(
            "/api/review",
            json={
                "answer_audit_id": answer.event_id,
                "reviewer_id": "reviewer-b",
                "decision": "approved",
                "notes": "source checked",
            },
        )
        verification = client.get("/api/audit/verify")
    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"
    assert response.json()["chain_valid"] is True
    assert verification.json()["valid"] is True
    assert verification.json()["events_checked"] == 2


def test_human_review_rejects_same_author_and_reviewer_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_module, "get_settings", lambda: _settings(tmp_path))
    with TestClient(api_module.app) as client:
        answer = client.app.state.runtime.audit.append_event(
            "answer_generated",
            "analyst-a",
            {"query": "機械学習", "answer": "draft"},
        )
        response = client.post(
            "/api/review",
            json={
                "answer_audit_id": answer.event_id,
                "reviewer_id": "analyst-a",
                "decision": "approved",
                "notes": "self review should fail",
            },
        )
    assert response.status_code == 409
    assert "must differ" in response.json()["detail"]


def test_generation_fails_closed_when_audit_chain_is_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(api_module, "get_settings", lambda: settings)
    with TestClient(api_module.app) as client:
        event = client.app.state.runtime.audit.append_event(
            "search_performed", "analyst-a", {"query": "original"}
        )
        with sqlite3.connect(settings.patent_rag_audit_db) as connection:
            connection.execute("DROP TRIGGER audit_events_no_update")
            connection.execute(
                "UPDATE audit_events SET payload_json = ? WHERE event_id = ?",
                ('{"query":"tampered"}', event.event_id),
            )
        response = client.post(
            "/api/answer",
            json={"query": "機械学習を用いた画像認識", "actor_id": "analyst-a"},
        )
    assert response.status_code == 503
    assert "Audit chain validation failed" in response.json()["detail"]
