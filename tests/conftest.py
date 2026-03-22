"""Shared fixtures (minimal config paths)."""

from __future__ import annotations

from pathlib import Path

import pytest

from voice_rag.config import VoiceRAGConfig


@pytest.fixture
def rag_config(tmp_path: Path) -> VoiceRAGConfig:
    """Isolated data dir; avoids touching repo ./data in unit tests."""
    return VoiceRAGConfig(
        data_dir=tmp_path / "data",
        llm_model="gpt-4o-mini",
        embed_mode="local",
        embed_model="sentence-transformers/all-MiniLM-L6-v2",
        top_k=3,
        chunk_size=100,
        chunk_overlap=10,
        strict_tenant=False,
    )
