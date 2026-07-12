"""Configuração central da aplicação."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "IFB Library Chat"
    app_env: str = "development"
    log_level: str = "INFO"
    max_upload_size_mb: int = Field(default=25, ge=1)

    documents_dir: Path = Path("pdfs_ifb")
    processed_dir: Path = Path("data/processed")
    ingest_chunk_size: int = Field(default=500, ge=50)
    ingest_chunk_overlap: int = Field(default=50, ge=0)
    ingest_device: str = "auto"
    chroma_dir: Path = Path("data/chroma")
    logs_dir: Path = Path("logs")
    chroma_collection: str = "ifb_tcc_matematica"

    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    embedding_batch_size: int = Field(default=32, ge=1)
    search_top_k: int = Field(default=5, ge=1)

    llm_provider: str = "none"
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = Field(default=None, repr=False)
    llm_timeout_seconds: float = Field(default=30.0, gt=0)

    local_llm_context_size: int = Field(default=2_048, ge=256)
    local_llm_max_tokens: int = Field(default=256, ge=32)
    local_llm_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    local_llm_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    local_llm_threads: int = Field(default=4, ge=1)
    local_llm_batch_size: int = Field(default=8, ge=1)
    local_llm_gpu_layers: int = Field(default=0, ge=0)
    local_llm_parallel_requests: int = Field(default=1, ge=1)
    local_llm_keep_alive: str = "5m"
    local_llm_model_path: str | None = None
    local_llm_kv_cache_type: str = "q4_k"
    local_llm_flash_attention: bool = False

    rag_context_token_budget: int = Field(default=1_600, ge=256)
    rag_output_token_reserve: int = Field(default=256, ge=32)
    rag_retrieval_top_k: int = Field(default=8, ge=1)
    rag_min_similarity: float = Field(default=0.35, ge=-1.0, le=1.0)
    rag_max_context_chars: int = Field(default=12_000, ge=500)
    rag_max_question_chars: int = Field(default=2_000, ge=1)
    rag_duplicate_threshold: float = Field(default=0.92, ge=0.0, le=1.0)

    ingest_max_concurrency: int = Field(default=2, ge=1)
    embedding_max_concurrency: int = Field(default=2, ge=1)

    def ensure_directories(self) -> None:
        for directory in (
            self.documents_dir,
            self.processed_dir,
            self.chroma_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
