from pathlib import Path
from unittest.mock import MagicMock

import pytest

from voice_rag.config import VoiceRAGConfig
from voice_rag.models import unit_metadata
from voice_rag.stores.chroma_store import ChromaVectorStore


@pytest.fixture
def tmp_config(tmp_path: Path) -> VoiceRAGConfig:
    return VoiceRAGConfig(
        data_dir=tmp_path / "data",
        embed_mode="local",
        embed_model="sentence-transformers/all-MiniLM-L6-v2",
        top_k=5,
        strict_tenant=False,
    )


def test_disabled_not_returned_by_default(
    tmp_config: VoiceRAGConfig,
    fake_embedder: MagicMock,
) -> None:
    store = ChromaVectorStore(tmp_config, fake_embedder)
    uid_on = "11111111-1111-1111-1111-111111111111"
    uid_off = "22222222-2222-2222-2222-222222222222"
    store.add_text_units(
        texts=["hello world alpha", "secret disabled chunk"],
        metadatas=[
            unit_metadata(
                unit_id=uid_on,
                unit_type="document_chunk",
                source_kind="document",
                source_uri="/a.txt",
                disabled=False,
            ),
            unit_metadata(
                unit_id=uid_off,
                unit_type="document_chunk",
                source_kind="document",
                source_uri="/b.txt",
                disabled=True,
            ),
        ],
        ids=[uid_on, uid_off],
    )
    _ids, metas, _d, docs = store.query("hello", top_k=10, include_disabled=False)
    found = {m.get("unit_id") for m in metas if m}
    assert uid_on in found
    assert uid_off not in found

    _ids2, metas2, _d2, _docs2 = store.query("secret", top_k=10, include_disabled=True)
    found2 = {m.get("unit_id") for m in metas2 if m}
    assert uid_off in found2


def test_strict_tenant_isolation(
    tmp_config: VoiceRAGConfig,
    fake_embedder: MagicMock,
) -> None:
    tmp_config.strict_tenant = True
    store = ChromaVectorStore(tmp_config, fake_embedder)
    ta = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    tb = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    store.add_text_units(
        texts=["tenant a content", "tenant b content"],
        metadatas=[
            unit_metadata(
                unit_id=ta,
                unit_type="document_chunk",
                source_kind="document",
                source_uri="/a.txt",
                tenant_id="A",
                disabled=False,
            ),
            unit_metadata(
                unit_id=tb,
                unit_type="document_chunk",
                source_kind="document",
                source_uri="/b.txt",
                tenant_id="B",
                disabled=False,
            ),
        ],
        ids=[ta, tb],
    )
    _ids, metas, _d, _docs = store.query("tenant", top_k=10, tenant_id="A", include_disabled=False)
    found = {m.get("unit_id") for m in metas if m}
    assert ta in found
    assert tb not in found
