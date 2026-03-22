from voice_rag.chunk import chunk_text


def test_chunk_basic() -> None:
    parts = chunk_text("abcdefgh", chunk_size=3, overlap=1)
    assert parts == ["abc", "cde", "efg", "gh"]


def test_chunk_empty() -> None:
    assert chunk_text("", chunk_size=10, overlap=2) == []
