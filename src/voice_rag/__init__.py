"""Voice RAG — voice + text knowledge pipeline with RAG. See SPEC.md."""

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

__all__ = [
    "Answer",
    "Citation",
    "IndexStats",
    "VoiceRAGConfig",
    "build_index_from_documents",
    "query",
    "__version__",
]

if TYPE_CHECKING:
    from voice_rag.config import VoiceRAGConfig
    from voice_rag.index import build_index_from_documents
    from voice_rag.models import Answer, Citation, IndexStats
    from voice_rag.rag import query


def __getattr__(name: str) -> Any:
    if name == "VoiceRAGConfig":
        from voice_rag.config import VoiceRAGConfig

        return VoiceRAGConfig
    if name in ("Answer", "Citation", "IndexStats"):
        from voice_rag import models

        return getattr(models, name)
    if name == "build_index_from_documents":
        from voice_rag.index import build_index_from_documents

        return build_index_from_documents
    if name == "query":
        from voice_rag.rag import query

        return query
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
