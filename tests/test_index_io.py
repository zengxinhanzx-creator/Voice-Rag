"""build_index_from_documents: file layout → IndexStats (no embedding if empty)."""

from __future__ import annotations

from pathlib import Path

from voice_rag.config import VoiceRAGConfig
from voice_rag.index import build_index_from_documents


def test_build_index_empty_paths_returns_zero_stats(tmp_path: Path) -> None:
    cfg = VoiceRAGConfig(data_dir=tmp_path / "d", chunk_size=50, chunk_overlap=5)
    stats = build_index_from_documents([], cfg)
    assert stats.documents_indexed == 0
    assert stats.chunks_created == 0
    assert stats.duration_ms == 0


def test_build_index_one_file_input_output(tmp_path: Path) -> None:
    """Input: one .md with known text → Output: 1 doc, chunk count matches chunk_text."""
    doc = tmp_path / "a.md"
    doc.write_text("alpha beta gamma delta epsilon\n", encoding="utf-8")
    cfg = VoiceRAGConfig(
        data_dir=tmp_path / "data",
        chunk_size=12,
        chunk_overlap=2,
    )
    stats = build_index_from_documents([doc], cfg, tenant_id="tenant-a")

    from voice_rag.chunk import chunk_text

    raw = doc.read_text(encoding="utf-8")
    expected_chunks = len(chunk_text(raw, cfg.chunk_size, cfg.chunk_overlap))

    assert stats.documents_indexed == 1
    assert stats.chunks_created == expected_chunks
    assert stats.duration_ms >= 0
