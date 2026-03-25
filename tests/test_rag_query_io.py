"""query(): I/O contract with mocked retrieval + LLM (no network, no ST load)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voice_rag.config import VoiceRAGConfig
from voice_rag.rag import query


def test_query_empty_text_returns_empty_answer(rag_config: VoiceRAGConfig) -> None:
    """Input: blank text → Output: empty text, no citations, model id preserved."""
    a = query("  ", None, rag_config)
    assert a.text == ""
    assert a.citations == []
    assert a.model_used == rag_config.llm_model
    assert a.trace_id is not None


def test_query_audio_raises(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="ASR"):
        query("hi", b"bytes", VoiceRAGConfig(data_dir=tmp_path))


@patch("litellm.completion")
@patch("voice_rag.rag.ChromaVectorStore")
def test_query_with_hits_filters_citations_to_allowed_ids(
    mock_store_cls: MagicMock,
    mock_completion: MagicMock,
    rag_config: VoiceRAGConfig,
) -> None:
    """LLM returns fake + real unit_id → only allowed ids in Answer.citations."""
    mock_store = mock_store_cls.return_value
    mock_store.query.return_value = (
        ["id-a"],
        [
            {
                "unit_id": "u-real",
                "unit_type": "document_chunk",
                "source_kind": "document",
                "source_uri": "/f.md",
            }
        ],
        [0.1],
        ["chunk body one two"],
    )
    mock_completion.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=(
                        '{"text":"summary","citations":['
                        '{"unit_id":"u-real","snippet":"one"},'
                        '{"unit_id":"not-in-retrieval","snippet":"x"}'
                        "]}"
                    )
                )
            )
        ]
    )

    out = query("what?", None, rag_config)

    assert out.text == "summary"
    assert len(out.citations) == 1
    assert out.citations[0].unit_id == "u-real"
    assert out.citations[0].snippet == "one"


@patch("litellm.completion")
@patch("voice_rag.rag.ChromaVectorStore")
def test_query_llm_failure_returns_no_citations(
    mock_store_cls: MagicMock,
    mock_completion: MagicMock,
    rag_config: VoiceRAGConfig,
) -> None:
    mock_store_cls.return_value.query.return_value = ([], [], [], [])
    mock_completion.side_effect = RuntimeError("api down")

    out = query("q", None, rag_config)

    assert "Generation failed" in out.text
    assert out.citations == []
