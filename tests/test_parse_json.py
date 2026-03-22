"""_parse_json_object: raw LLM string → dict."""

from __future__ import annotations

import pytest

from voice_rag.rag import _parse_json_object


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"text": "a", "citations": []}', {"text": "a", "citations": []}),
        (
            '```json\n{"text": "x", "citations": [{"unit_id": "u1"}]}\n```',
            {"text": "x", "citations": [{"unit_id": "u1"}]},
        ),
        (
            '```\n{"foo": 1}\n```',
            {"foo": 1},
        ),
    ],
    ids=["plain", "fenced_json", "fenced_plain"],
)
def test_parse_json_ok(raw: str, expected: dict) -> None:
    assert _parse_json_object(raw) == expected


def test_parse_json_invalid() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        _parse_json_object("not json at all")
