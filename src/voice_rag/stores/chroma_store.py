from __future__ import annotations

import uuid
from typing import Any

import chromadb

from voice_rag.config import VoiceRAGConfig
from voice_rag.embed import Embedder

COLLECTION = "voice_rag_units"


def build_where(
    *,
    include_disabled: bool,
    tenant_id: str | None,
    strict_tenant: bool,
) -> dict[str, Any] | None:
    """Chroma `where` filter: FR-R7 disabled; SPEC §4.4 FR-I4 tenant."""
    parts: list[dict[str, Any]] = []
    if not include_disabled:
        parts.append({"disabled": False})
    if tenant_id is not None:
        if strict_tenant:
            parts.append({"tenant_id": tenant_id})
        else:
            parts.append({"$or": [{"tenant_id": tenant_id}, {"tenant_id": ""}]})
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return {"$and": parts}


class ChromaVectorStore:
    def __init__(self, config: VoiceRAGConfig, embedder: Embedder) -> None:
        self._config = config
        self._embedder = embedder
        config.data_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(config.vector_store_path()))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def add_text_units(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        if not texts:
            return
        embeddings = self._embedder.embed(texts)
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        emb_list = [e.tolist() for e in embeddings]
        clean_meta: list[dict[str, Any]] = []
        for m in metadatas:
            clean: dict[str, Any] = {}
            for k, v in m.items():
                if v is None:
                    clean[k] = ""
                elif isinstance(v, bool):
                    clean[k] = v
                elif isinstance(v, (int, float)):
                    clean[k] = v
                else:
                    clean[k] = str(v)
            clean_meta.append(clean)
        self._collection.upsert(ids=ids, embeddings=emb_list, documents=texts, metadatas=clean_meta)

    def query(
        self,
        query_text: str,
        top_k: int,
        tenant_id: str | None = None,
        include_disabled: bool = False,
    ) -> tuple[list[str], list[dict[str, Any]], list[float]]:
        qemb = self._embedder.embed_query(query_text)
        where = build_where(
            include_disabled=include_disabled,
            tenant_id=tenant_id,
            strict_tenant=self._config.strict_tenant,
        )
        kwargs: dict[str, Any] = {
            "query_embeddings": [qemb.tolist()],
            "n_results": top_k,
            "include": ["metadatas", "documents", "distances"],
        }
        if where:
            kwargs["where"] = where
        res = self._collection.query(**kwargs)
        ids = res["ids"][0] if res.get("ids") else []
        metas = res["metadatas"][0] if res.get("metadatas") else []
        dists = res["distances"][0] if res.get("distances") else []
        docs = res["documents"][0] if res.get("documents") else []
        return ids, metas, dists, docs

    def count(self) -> int:
        return self._collection.count()
