from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VoiceRAGConfig(BaseSettings):
    """Runtime configuration (SPEC §8). Loaded from environment."""

    model_config = SettingsConfigDict(
        env_prefix="VOICERAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_model: str = Field(default="gpt-4o-mini", description="LiteLLM model id")
    extract_model: str | None = Field(default=None, description="Optional override for extraction")
    embed_mode: Literal["local", "litellm"] = "local"
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    data_dir: Path = Path("./data")
    top_k: int = 5
    chunk_size: int = 800
    chunk_overlap: int = 100
    rrf_k: int = 60
    strict_tenant: bool = False
    log_level: str = "INFO"
    admin_token: str | None = None

    @field_validator("strict_tenant", mode="before")
    @classmethod
    def _coerce_strict_tenant(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if v in (0, 1):
            return bool(v)
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("0", "false", "no", ""):
                return False
            if s in ("1", "true", "yes"):
                return True
        return bool(v)

    @classmethod
    def from_env(cls, overrides: dict | None = None) -> VoiceRAGConfig:
        if overrides:
            return cls(**overrides)
        return cls()

    def vector_store_path(self) -> Path:
        return self.data_dir / "vector_store"
