from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from voice_rag.config import VoiceRAGConfig
from voice_rag.rag import query as rag_query

logger = logging.getLogger(__name__)


class QueryBody(BaseModel):
    text: str = Field(..., min_length=1)
    tenant_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=100)
    include_disabled: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = VoiceRAGConfig.from_env()
    logging.basicConfig(level=getattr(logging, app.state.config.log_level.upper(), logging.INFO))
    yield


app = FastAPI(
    title="Voice RAG",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(request: Request) -> dict[str, Any]:
    c: VoiceRAGConfig = request.app.state.config
    return {
        "status": "ok",
        "llm_model": c.llm_model,
        "embed_mode": c.embed_mode,
    }


@app.post("/api/v1/query")
def post_query(body: QueryBody, request: Request) -> dict[str, Any]:
    c: VoiceRAGConfig = request.app.state.config
    answer = rag_query(
        body.text,
        None,
        c,
        tenant_id=body.tenant_id,
        top_k=body.top_k,
        include_disabled=body.include_disabled,
    )
    return answer.to_json_dict()
