"""CLI (SPEC §4.7)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer

from voice_rag.config import VoiceRAGConfig
from voice_rag.index import build_index_from_documents
from voice_rag.rag import query as rag_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Voice RAG — index documents and query the vector store.")


@app.command("index-docs")
def index_docs(
    paths: Annotated[list[Path], typer.Argument(help=".txt / .md files or directories")],
    tenant_id: Annotated[str | None, typer.Option(help="Tenant id for indexed units")] = None,
    voice_transform: Annotated[
        bool, typer.Option(help="Reserved for P1.1 voice-ready transform")
    ] = False,
) -> None:
    """Index local documents into the Chroma vector store."""
    config = VoiceRAGConfig.from_env()
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    stats = build_index_from_documents(
        paths,
        config,
        voice_transform=voice_transform,
        tenant_id=tenant_id,
    )
    typer.echo(
        json.dumps(
            {
                "documents_indexed": stats.documents_indexed,
                "chunks_created": stats.chunks_created,
                "duration_ms": stats.duration_ms,
            },
            indent=2,
        )
    )


@app.command("ask")
def ask(
    question: Annotated[str, typer.Argument(help="Question text")],
    tenant_id: Annotated[str | None, typer.Option(help="Tenant filter")] = None,
    top_k: Annotated[int | None, typer.Option(help="Retrieve top-k")] = None,
) -> None:
    """Run one RAG query and print JSON (answer + citations)."""
    config = VoiceRAGConfig.from_env()
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    try:
        answer = rag_query(question, None, config, tenant_id=tenant_id, top_k=top_k)
    except NotImplementedError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e
    typer.echo(json.dumps(answer.to_json_dict(), indent=2, ensure_ascii=False))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
