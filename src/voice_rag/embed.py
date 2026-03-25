from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from voice_rag.config import VoiceRAGConfig


class Embedder:
    """Text embeddings: local sentence-transformers or LiteLLM API."""

    def __init__(self, config: VoiceRAGConfig) -> None:
        self._config = config
        self._local_model = None

    def _load_local(self):
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer

            try:
                self._local_model = SentenceTransformer(self._config.embed_model)
            except Exception as e:
                raise RuntimeError(
                    "Failed to load local embedding model "
                    f"{self._config.embed_model!r}. "
                    "Ensure outbound HTTPS to Hugging Face works on first run, "
                    "or set HF_HUB_OFFLINE=1 if the model is already cached. "
                    "Alternatively set VOICERAG_EMBED_MODE=litellm and VOICERAG_EMBED_MODEL "
                    "to an API embedding model (with the right API keys)."
                ) from e
        return self._local_model

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._config.embed_mode == "local":
            model = self._load_local()
            emb = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return np.asarray(emb, dtype=np.float32)
        return self._embed_litellm(texts)

    def _embed_litellm(self, texts: list[str]) -> np.ndarray:
        import litellm

        vecs = []
        for t in texts:
            r = litellm.embedding(model=self._config.embed_model, input=t)
            vecs.append(r["data"][0]["embedding"])
        return np.asarray(vecs, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
