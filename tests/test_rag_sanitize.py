from voice_rag.rag import _sanitize_citations


def test_sanitize_drops_unknown_unit_id() -> None:
    allowed = {
        "u1": {
            "unit_type": "document_chunk",
            "source_kind": "document",
            "source_uri": "/a.md",
        }
    }
    cites = _sanitize_citations(
        [
            {"unit_id": "u1", "snippet": "x"},
            {"unit_id": "fake", "snippet": "y"},
        ],
        allowed,
    )
    assert len(cites) == 1
    assert cites[0].unit_id == "u1"
