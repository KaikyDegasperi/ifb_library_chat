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

    documents_dir: Path = Path("pdfs_ifb")
    processed_dir: Path = Path("data/processed")
    chroma_dir: Path = Path("data/chroma")
    logs_dir: Path = Path("logs")
    chroma_collection: str = "ifb_tcc_matematica"

    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    llm_provider: str = "none"
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = Field(default=None, repr=False)

    def ensure_directories(self) -> None:
        for directory in (
            self.documents_dir,
            self.processed_dir,
            self.chroma_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
