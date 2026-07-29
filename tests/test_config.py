from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_ensure_directories(tmp_path: Path) -> None:
    settings = Settings(
        documents_dir=tmp_path / "documents",
        processed_dir=tmp_path / "processed",
        chroma_dir=tmp_path / "chroma",
        logs_dir=tmp_path / "logs",
    )

    settings.ensure_directories()

    assert settings.documents_dir.is_dir()
    assert settings.processed_dir.is_dir()
    assert settings.chroma_dir.is_dir()
    assert settings.logs_dir.is_dir()


def test_production_requires_admin_token(monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    with pytest.raises(ValidationError, match="ADMIN_API_TOKEN"):
        Settings(app_env="production", admin_api_token=None, _env_file=None)


def test_admin_token_is_masked_by_settings() -> None:
    token = "secret-value-that-must-stay-private"
    settings = Settings(admin_api_token=token, _env_file=None)

    assert settings.admin_token_value == token
    assert token not in repr(settings)
    assert token not in str(settings.model_dump())


def test_metrics_details_can_be_enabled_by_environment(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_DETAILS_ENABLED", "true")

    settings = Settings(_env_file=None)

    assert settings.metrics_details_enabled is True


def test_bm25_is_the_default_retrieval_provider() -> None:
    settings = Settings(_env_file=None)

    assert settings.retrieval_provider == "bm25"
    assert settings.bm25_k1 == 1.5
    assert settings.bm25_b == 0.75


def test_retrieval_provider_is_validated() -> None:
    with pytest.raises(ValidationError, match="RETRIEVAL_PROVIDER"):
        Settings(retrieval_provider="unsupported", _env_file=None)


def test_docs_are_disabled_by_default_only_in_production() -> None:
    development = Settings(app_env="development", _env_file=None)
    production = Settings(
        app_env="production",
        admin_api_token="strong-production-token",
        _env_file=None,
    )
    explicit = Settings(
        app_env="production",
        admin_api_token="strong-production-token",
        api_docs_enabled=True,
        _env_file=None,
    )

    assert development.docs_enabled is True
    assert production.docs_enabled is False
    assert explicit.docs_enabled is True


def test_production_rejects_wildcard_or_insecure_cors() -> None:
    with pytest.raises(ValidationError, match="não pode conter"):
        Settings(
            app_env="production",
            admin_api_token="strong-production-token",
            cors_allowed_origins=["*"],
            _env_file=None,
        )
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            app_env="production",
            admin_api_token="strong-production-token",
            cors_allowed_origins=["http://biblioteca.example"],
            _env_file=None,
        )


def test_request_limit_must_cover_upload_limit() -> None:
    with pytest.raises(ValidationError, match="MAX_REQUEST_SIZE_MB"):
        Settings(
            max_upload_size_mb=25,
            max_request_size_mb=20,
            _env_file=None,
        )
