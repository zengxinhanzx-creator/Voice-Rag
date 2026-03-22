"""chunk_text: explicit input → output (character windows, SPEC §4.1 FR-D2)."""

from __future__ import annotations

import pytest

from voice_rag.chunk import chunk_text


@pytest.mark.parametrize(
    ("text", "chunk_size", "overlap", "expected"),
    [
        ("abcdefgh", 3, 1, ["abc", "cde", "efg", "gh"]),
        ("hello", 10, 2, ["hello"]),
        ("abcd", 2, 0, ["ab", "cd"]),
        ("  spaced  ", 100, 10, ["spaced"]),
    ],
    ids=["overlap_1", "single_chunk", "no_overlap", "strip_outer"],
)
def test_chunk_text_parametrized(
    text: str,
    chunk_size: int,
    overlap: int,
    expected: list[str],
) -> None:
    assert chunk_text(text, chunk_size, overlap) == expected


def test_chunk_empty_input() -> None:
    assert chunk_text("", chunk_size=10, overlap=2) == []


def test_chunk_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("abc", chunk_size=3, overlap=3)


def test_chunk_invalid_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_text("abc", chunk_size=0, overlap=0)
