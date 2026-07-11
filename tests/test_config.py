from pathlib import Path

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
