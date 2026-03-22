from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

import litellm

from voice_rag.config import VoiceRAGConfig
from voice_rag.embed import Embedder
from voice_rag.models import Answer, Citation
from voice_rag.stores.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)


def _parse_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    raise ValueError("Model did not return valid JSON")


def _sanitize_citations(
    citations: list[Any],
    allowed: dict[str, dict[str, Any]],
) -> list[Citation]:
    out: list[Citation] = []
    for c in citations:
        if not isinstance(c, dict):
            continue
        uid = c.get("unit_id")
        if uid not in allowed:
            continue
        meta = allowed[uid]
        snip = c.get("snippet")
        if not isinstance(snip, str):
            snip = None
        out.append(
            Citation(
                unit_id=str(uid),
                unit_type=str(meta.get("unit_type", "")),
                source_kind=str(meta.get("source_kind", "")),
                source_uri=str(meta.get("source_uri", "")),
                t_start_ms=c.get("t_start_ms") if isinstance(c.get("t_start_ms"), int) else None,
                t_end_ms=c.get("t_end_ms") if isinstance(c.get("t_end_ms"), int) else None,
                snippet=snip,
            )
        )
    return out


def query(
    text: str | None,
    audio: Path | bytes | None,
    config: VoiceRAGConfig,
    *,
    tenant_id: str | None = None,
    top_k: int | None = None,
    include_disabled: bool = False,
) -> Answer:
    """RAG query with LiteLLM generation and citations (SPEC §7)."""
    trace_id = str(uuid.uuid4())
    if audio is not None:
        raise NotImplementedError("Audio query requires ASR (P1); pass text= for P0.")

    if not text or not text.strip():
        return Answer(
            text="",
            citations=[],
            model_used=config.llm_model,
            trace_id=trace_id,
        )

    k = top_k if top_k is not None else config.top_k
    embedder = Embedder(config)
    store = ChromaVectorStore(config, embedder)
    _ids, metadatas, _dists, documents = store.query(
        text.strip(),
        top_k=k,
        tenant_id=tenant_id,
        include_disabled=include_disabled,
    )

    allowed: dict[str, dict[str, Any]] = {}
    context_blocks: list[str] = []
    for meta, doc in zip(metadatas, documents, strict=False):
        if not meta:
            continue
        uid = meta.get("unit_id")
        if not uid:
            continue
        uid_s = str(uid)
        row = dict(meta)
        allowed[uid_s] = row
        meta_line = (
            f"unit_type={row.get('unit_type', '')}, "
            f"source_kind={row.get('source_kind', '')}, "
            f"source_uri={row.get('source_uri', '')}"
        )
        context_blocks.append(f"[unit_id={uid_s}]\n{meta_line}\n\n{doc or ''}")

    if not context_blocks:
        user_prompt = (
            "No retrieved context. Reply that you have no indexed sources, "
            "and answer briefly without inventing citations. "
            'Return JSON only: {"text": string, "citations": []}'
        )
        ctx = ""
    else:
        ctx = "\n\n---\n\n".join(context_blocks)
        user_prompt = (
            "Use ONLY the context below to answer. "
            "Return JSON with keys text (string) and citations (array). "
            "Each citation MUST include unit_id copied from the context headers. "
            "Include unit_type, source_kind, source_uri for that unit_id; "
            "optional snippet (short quote from context). "
            "If context is insufficient, say so and use citations: [].\n\n"
            f"Context:\n{ctx}"
        )

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant for enterprise knowledge. Output JSON only.",
        },
        {"role": "user", "content": user_prompt + f"\n\nQuestion: {text.strip()}"},
    ]

    try:
        resp = litellm.completion(
            model=config.llm_model,
            messages=messages,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or ""
        data = _parse_json_object(raw)
    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        return Answer(
            text=f"Generation failed: {e!s}",
            citations=[],
            model_used=config.llm_model,
            trace_id=trace_id,
        )

    answer_text = data.get("text", "")
    if not isinstance(answer_text, str):
        answer_text = str(answer_text)
    raw_cites = data.get("citations", [])
    if not isinstance(raw_cites, list):
        raw_cites = []

    cites = _sanitize_citations(raw_cites, allowed)

    return Answer(
        text=answer_text,
        citations=cites,
        model_used=config.llm_model,
        trace_id=trace_id,
    )
