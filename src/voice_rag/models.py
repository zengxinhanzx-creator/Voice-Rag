from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class Citation:
    unit_id: str
    unit_type: str
    source_kind: str
    source_uri: str
    t_start_ms: int | None = None
    t_end_ms: int | None = None
    snippet: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "source_kind": self.source_kind,
            "source_uri": self.source_uri,
            "t_start_ms": self.t_start_ms,
            "t_end_ms": self.t_end_ms,
            "snippet": self.snippet,
        }


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    model_used: str
    trace_id: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "citations": [c.to_json_dict() for c in self.citations],
            "model_used": self.model_used,
            "trace_id": self.trace_id,
        }


@dataclass
class IndexStats:
    documents_indexed: int = 0
    chunks_created: int = 0
    duration_ms: int = 0


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def unit_metadata(
    *,
    unit_id: str,
    unit_type: str,
    source_kind: str,
    source_uri: str,
    tenant_id: str | None = None,
    disabled: bool = False,
    topic_label: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Flatten metadata for Chroma (SPEC §6.2 subset)."""
    return {
        "unit_id": unit_id,
        "unit_type": unit_type,
        "source_kind": source_kind,
        "source_uri": source_uri,
        "tenant_id": tenant_id or "",
        "disabled": disabled,
        "topic_label": topic_label or "",
        "created_at": created_at or utc_now_iso(),
    }
