"""Configuração central da aplicação."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
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
    metrics_details_enabled: bool = False
    api_docs_enabled: bool | None = None
    cors_allowed_origins: list[str] = Field(default_factory=list)
    search_max_query_chars: int = Field(default=2_000, ge=1, le=10_000)
    api_max_top_k: int = Field(default=50, ge=1, le=100)
    api_max_filter_chars: int = Field(default=500, ge=1, le=2_000)
    max_upload_size_mb: int = Field(default=25, ge=1, le=500)
    max_request_size_mb: int = Field(default=30, ge=1, le=550)
    max_upload_filename_chars: int = Field(default=180, ge=20, le=255)
    admin_api_token: SecretStr | None = Field(default=None, repr=False)

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
    retrieval_provider: str = "bm25"
    bm25_k1: float = Field(default=1.5, gt=0)
    bm25_b: float = Field(default=0.75, ge=0, le=1)

    llm_provider: str = "none"
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = Field(default=None, repr=False)
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    llm_max_tokens: int = Field(default=256, ge=1)

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
    rag_candidate_pool_size: int = Field(default=24, ge=1)
    rag_lexical_promotion_slots: int = Field(default=2, ge=0)
    rag_min_similarity: float = Field(default=0.35, ge=-1.0, le=1.0)
    rag_max_context_chars: int = Field(default=12_000, ge=500)
    rag_max_question_chars: int = Field(default=2_000, ge=1, le=10_000)
    rag_duplicate_threshold: float = Field(default=0.92, ge=0.0, le=1.0)

    ingest_max_concurrency: int = Field(default=2, ge=1)
    embedding_max_concurrency: int = Field(default=2, ge=1)

    @field_validator("cors_allowed_origins")
    @classmethod
    def normalize_cors_origins(cls, origins: list[str]) -> list[str]:
        normalized = [origin.strip().rstrip("/") for origin in origins if origin.strip()]
        return list(dict.fromkeys(normalized))

    @field_validator("retrieval_provider")
    @classmethod
    def validate_retrieval_provider(cls, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in {"bm25", "dense"}:
            raise ValueError("RETRIEVAL_PROVIDER deve ser bm25 ou dense")
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.rag_lexical_promotion_slots > self.rag_retrieval_top_k:
            raise ValueError(
                "RAG_LEXICAL_PROMOTION_SLOTS não pode exceder RAG_RETRIEVAL_TOP_K"
            )
        if self.max_request_size_mb < self.max_upload_size_mb:
            raise ValueError(
                "MAX_REQUEST_SIZE_MB deve ser maior ou igual a MAX_UPLOAD_SIZE_MB"
            )
        if self.is_production:
            if not self.admin_token_value:
                raise ValueError("ADMIN_API_TOKEN é obrigatório em produção")
            if any(origin == "*" for origin in self.cors_allowed_origins):
                raise ValueError("CORS_ALLOWED_ORIGINS não pode conter * em produção")
            insecure_origins = [
                origin
                for origin in self.cors_allowed_origins
                if not origin.casefold().startswith("https://")
            ]
            if insecure_origins:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS deve usar HTTPS em produção"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @property
    def docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return not self.is_production

    @property
    def admin_token_value(self) -> str | None:
        if self.admin_api_token is None:
            return None
        value = self.admin_api_token.get_secret_value().strip()
        return value or None

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

    @property
    def max_request_size_bytes(self) -> int:
        return self.max_request_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
