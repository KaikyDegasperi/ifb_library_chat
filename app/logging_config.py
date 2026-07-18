"""Logging uniforme em formato chave=valor."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_OBSERVABILITY_FIELDS = (
    "request_id",
    "endpoint",
    "status",
    "duration_ms",
    "source_count",
    "context_chars",
    "error_type",
    "embedding_time_ms",
    "vector_search_time_ms",
    "context_preparation_time_ms",
    "generation_time_ms",
)


def _safe_value(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        message = record.getMessage().replace("\n", "\\n")
        base = (
            f'timestamp="{timestamp}" level={record.levelname} '
            f'logger="{record.name}" message="{message}"'
        )
        fields = "".join(
            f' {name}="{_safe_value(getattr(record, name))}"'
            for name in _OBSERVABILITY_FIELDS
            if hasattr(record, name)
        )
        return f"{base}{fields}"


def configure_logging(level: str, logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = StructuredFormatter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    root.addHandler(console)
    root.addHandler(file_handler)
