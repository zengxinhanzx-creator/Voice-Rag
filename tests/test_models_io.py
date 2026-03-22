"""models: JSON-friendly shapes (SPEC §6.5–6.6)."""

from __future__ import annotations

from voice_rag.models import Answer, Citation, unit_metadata


def test_citation_to_json_dict() -> None:
    c = Citation(
        unit_id="u1",
        unit_type="document_chunk",
        source_kind="document",
        source_uri="/a.md",
        t_start_ms=None,
        t_end_ms=None,
        snippet="quote",
    )
    d = c.to_json_dict()
    assert d == {
        "unit_id": "u1",
        "unit_type": "document_chunk",
        "source_kind": "document",
        "source_uri": "/a.md",
        "t_start_ms": None,
        "t_end_ms": None,
        "snippet": "quote",
    }


def test_answer_to_json_dict() -> None:
    a = Answer(
        text="hello",
        citations=[
            Citation(
                unit_id="u1",
                unit_type="document_chunk",
                source_kind="document",
                source_uri="/x.txt",
            )
        ],
        model_used="gpt-4o-mini",
        trace_id="tr-1",
    )
    d = a.to_json_dict()
    assert d["text"] == "hello"
    assert d["model_used"] == "gpt-4o-mini"
    assert d["trace_id"] == "tr-1"
    assert len(d["citations"]) == 1
    assert d["citations"][0]["unit_id"] == "u1"


def test_unit_metadata_defaults() -> None:
    m = unit_metadata(
        unit_id="id1",
        unit_type="document_chunk",
        source_kind="document",
        source_uri="/p.md",
    )
    assert m["tenant_id"] == ""
    assert m["disabled"] is False
    assert m["topic_label"] == ""
    assert "created_at" in m
