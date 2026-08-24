import sqlite3
from pathlib import Path

import pytest

from patent_rag.audit import AuditStore


def test_answer_and_human_review_form_valid_hash_chain(tmp_path: Path) -> None:
    store = AuditStore(tmp_path / "audit.sqlite3")
    answer = store.append_event(
        "answer_generated",
        "analyst-a",
        {"query": "機械学習", "answer": "根拠付き回答", "initial_review_status": "pending"},
    )
    review = store.record_review(answer.event_id, "reviewer-b", "approved", "根拠を確認")

    assert store.latest_review_status(answer.event_id) == "approved"
    assert store.get_event(review.event_id)["subject_event_id"] == answer.event_id  # type: ignore[index]
    assert store.verify_chain()["valid"] is True
    assert store.verify_chain()["events_checked"] == 2


def test_hash_chain_detects_payload_tampering(tmp_path: Path) -> None:
    database = tmp_path / "audit.sqlite3"
    store = AuditStore(database)
    receipt = store.append_event("search_performed", "analyst-a", {"query": "original"})
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TRIGGER audit_events_no_update")
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = ?",
            ('{"query":"tampered"}', receipt.event_id),
        )
    verification = store.verify_chain()
    assert verification["valid"] is False
    assert verification["failed_sequence"] == 1


def test_database_triggers_reject_update_and_delete(tmp_path: Path) -> None:
    database = tmp_path / "audit.sqlite3"
    store = AuditStore(database)
    receipt = store.append_event("search_performed", "analyst-a", {"query": "original"})
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE audit_events SET actor_id = 'other' WHERE event_id = ?",
                (receipt.event_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM audit_events WHERE event_id = ?",
                (receipt.event_id,),
            )


def test_review_requires_existing_answer_event(tmp_path: Path) -> None:
    store = AuditStore(tmp_path / "audit.sqlite3")
    with pytest.raises(ValueError, match="does not exist"):
        store.record_review("missing", "reviewer", "rejected", "no answer")
