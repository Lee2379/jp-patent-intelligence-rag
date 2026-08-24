from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

GENESIS_HASH = "0" * 64
ReviewDecision = Literal["approved", "needs_revision", "rejected"]


@dataclass(frozen=True, slots=True)
class AuditReceipt:
    event_id: str
    event_hash: str
    occurred_at: str


class AuditStore:
    """Local append-only event log with a verifiable SHA-256 hash chain."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    subject_event_id TEXT,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    FOREIGN KEY(subject_event_id) REFERENCES audit_events(event_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_events(subject_event_id)"
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END
                """
            )

    @staticmethod
    def _canonical_event(
        *,
        event_id: str,
        occurred_at: str,
        event_type: str,
        actor_id: str,
        subject_event_id: str | None,
        payload_json: str,
        previous_hash: str,
    ) -> bytes:
        value = {
            "actor_id": actor_id,
            "event_id": event_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "payload": json.loads(payload_json),
            "previous_hash": previous_hash,
            "subject_event_id": subject_event_id,
        }
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def append_event(
        self,
        event_type: str,
        actor_id: str,
        payload: dict[str, Any],
        *,
        subject_event_id: str | None = None,
    ) -> AuditReceipt:
        event_id = str(uuid.uuid4())
        occurred_at = datetime.now(UTC).isoformat()
        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous_row = connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = str(previous_row["event_hash"]) if previous_row else GENESIS_HASH
            event_hash = hashlib.sha256(
                self._canonical_event(
                    event_id=event_id,
                    occurred_at=occurred_at,
                    event_type=event_type,
                    actor_id=actor_id,
                    subject_event_id=subject_event_id,
                    payload_json=payload_json,
                    previous_hash=previous_hash,
                )
            ).hexdigest()
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, occurred_at, event_type, actor_id, subject_event_id,
                    payload_json, previous_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    occurred_at,
                    event_type,
                    actor_id,
                    subject_event_id,
                    payload_json,
                    previous_hash,
                    event_hash,
                ),
            )
        return AuditReceipt(event_id, event_hash, occurred_at)

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "sequence": int(row["sequence"]),
            "event_id": str(row["event_id"]),
            "occurred_at": str(row["occurred_at"]),
            "event_type": str(row["event_type"]),
            "actor_id": str(row["actor_id"]),
            "subject_event_id": row["subject_event_id"],
            "payload": json.loads(row["payload_json"]),
            "previous_hash": str(row["previous_hash"]),
            "event_hash": str(row["event_hash"]),
        }

    def record_review(
        self,
        answer_event_id: str,
        reviewer_id: str,
        decision: ReviewDecision,
        notes: str,
    ) -> AuditReceipt:
        answer_event = self.get_event(answer_event_id)
        if answer_event is None or answer_event["event_type"] != "answer_generated":
            raise ValueError("The reviewed answer audit event does not exist")
        if answer_event["actor_id"] == reviewer_id:
            raise ValueError("Reviewer label must differ from the answer author label")
        return self.append_event(
            "review_decision",
            reviewer_id,
            {"decision": decision, "notes": notes},
            subject_event_id=answer_event_id,
        )

    def latest_review_status(self, answer_event_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM audit_events
                WHERE event_type = 'review_decision' AND subject_event_id = ?
                ORDER BY sequence DESC LIMIT 1
                """,
                (answer_event_id,),
            ).fetchone()
        if row is None:
            answer_event = self.get_event(answer_event_id)
            if answer_event is None:
                return "pending"
            return str(answer_event["payload"].get("initial_review_status", "pending"))
        return str(json.loads(row["payload_json"])["decision"])

    def verify_chain(self) -> dict[str, Any]:
        previous_hash = GENESIS_HASH
        checked = 0
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
        for row in rows:
            expected = hashlib.sha256(
                self._canonical_event(
                    event_id=str(row["event_id"]),
                    occurred_at=str(row["occurred_at"]),
                    event_type=str(row["event_type"]),
                    actor_id=str(row["actor_id"]),
                    subject_event_id=row["subject_event_id"],
                    payload_json=str(row["payload_json"]),
                    previous_hash=previous_hash,
                )
            ).hexdigest()
            if str(row["previous_hash"]) != previous_hash or str(row["event_hash"]) != expected:
                return {
                    "valid": False,
                    "events_checked": checked,
                    "failed_sequence": int(row["sequence"]),
                }
            previous_hash = str(row["event_hash"])
            checked += 1
        return {
            "valid": True,
            "events_checked": checked,
            "head_hash": previous_hash,
        }

    def export_receipt(self, receipt: AuditReceipt) -> dict[str, str]:
        return asdict(receipt)
