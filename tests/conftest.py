"""Shared fixtures (minimal config paths)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from voice_rag.config import VoiceRAGConfig

# Chroma cosine collections expect fixed embedding width (all-MiniLM-L6-v2 = 384).
_FAKE_EMBED_DIM = 384


@pytest.fixture
def fake_embedder() -> MagicMock:
    """Deterministic vectors; no Hugging Face download (offline-safe tests)."""
    m = MagicMock()
    m.embed.side_effect = lambda texts: np.ones((len(texts), _FAKE_EMBED_DIM), dtype=np.float32)
    m.embed_query.side_effect = lambda _t: np.ones(_FAKE_EMBED_DIM, dtype=np.float32)
    return m


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
