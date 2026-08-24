from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PatentSection:
    name: str
    text: str


@dataclass(slots=True)
class PatentDocument:
    document_id: str
    year: int
    publication_kind: str
    local_path: str
    abstract: str
    claims: list[str]
    sections: list[PatentSection]
    ai_score: int
    source_license: str = "CC BY 4.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PatentChunk:
    chunk_id: str
    document_id: str
    year: int
    publication_kind: str
    section: str
    text: str
    local_path: str
    ai_score: int
    ordinal: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
