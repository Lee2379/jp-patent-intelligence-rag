from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    patent_rag_data_dir: Path = Path("data/processed")
    patent_rag_index_dir: Path = Path("artifacts/index")
    patent_rag_cache_dir: Path = Path("artifacts/cache")
    patent_rag_audit_db: Path = Path("artifacts/audit/audit.sqlite3")
    patent_rag_top_k: int = 4
    patent_rag_min_dense_score: float = 0.81
    ollama_base_url: str = "http://127.0.0.1:11435"
    ollama_model: str = "qwen3:1.7b"
    ollama_timeout_seconds: float = 180.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
