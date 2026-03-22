from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from voice_rag.chunk import chunk_text
from voice_rag.config import VoiceRAGConfig
from voice_rag.embed import Embedder
from voice_rag.models import IndexStats, unit_metadata
from voice_rag.stores.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)

_DOC_SUFFIX = {".txt", ".md"}


def _collect_document_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        p = p.expanduser().resolve()
        if p.is_file():
            if p.suffix.lower() in _DOC_SUFFIX:
                out.append(p)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in _DOC_SUFFIX:
                    out.append(f)
    return sorted(set(out))


def build_index_from_documents(
    paths: list[Path],
    config: VoiceRAGConfig,
    *,
    voice_transform: bool = False,
    tenant_id: str | None = None,
) -> IndexStats:
    """Index local .txt / .md into the vector store (SPEC §7)."""
    if voice_transform:
        logger.warning(
            "voice_transform=True: P0 uses document_chunk only; full voice-ready T4 is P1.1"
        )

    t0 = time.perf_counter()
    files = _collect_document_files(paths)
    if not files:
        return IndexStats(documents_indexed=0, chunks_created=0, duration_ms=0)

    embedder = Embedder(config)
    store = ChromaVectorStore(config, embedder)

    texts: list[str] = []
    metas: list[dict[str, Any]] = []
    ids: list[str] = []
    docs_count = 0

    for path in files:
        docs_count += 1
        raw = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_text(raw, config.chunk_size, config.chunk_overlap)
        resolved = str(path.resolve())
        for i, chunk in enumerate(chunks):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"document:{resolved}:{i}"))
            texts.append(chunk)
            ids.append(uid)
            metas.append(
                unit_metadata(
                    unit_id=uid,
                    unit_type="document_chunk",
                    source_kind="document",
                    source_uri=resolved,
                    tenant_id=tenant_id,
                    disabled=False,
                )
            )

    store.add_text_units(texts, metas, ids=ids)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    return IndexStats(
        documents_indexed=docs_count,
        chunks_created=len(texts),
        duration_ms=duration_ms,
    )
