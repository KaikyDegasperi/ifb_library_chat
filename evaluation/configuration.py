"""Captura segura das configurações e do corpus, sem credenciais."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.runtime import runtime_configuration


def code_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def safe_settings(settings: Settings) -> dict[str, Any]:
    configuration = runtime_configuration(settings)
    # Campo legado mantido nos novos resultados para leitores antigos.
    return {
        **configuration,
        "similarity_threshold": configuration["relevance_threshold"],
    }


def configuration_fingerprint(configuration: dict[str, Any]) -> str:
    canonical = json.dumps(
        configuration,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def runtime_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "chromadb": importlib.metadata.version("chromadb"),
        "docling": importlib.metadata.version("docling"),
        "transformers": importlib.metadata.version("transformers"),
    }


def validate_runtime_configuration(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[str]:
    """Compara a configuração congelada com a API realmente em execução."""
    keys = runtime_configuration(Settings(_env_file=None)).keys()
    errors: list[str] = []
    for key in keys:
        if key not in expected:
            errors.append(f"configuração congelada não contém {key}")
        elif actual.get(key) != expected.get(key):
            errors.append(
                f"{key}: congelado={expected.get(key)!r}, API={actual.get(key)!r}"
            )
    return errors


def frozen_configuration(
    settings: Settings,
    benchmark_version: str,
    seed: int,
) -> dict[str, Any]:
    configuration = safe_settings(settings)
    return {
        "status": "frozen",
        "experiment": "official_bm25_end_to_end",
        "target_split": "final",
        **configuration,
        "configuration_fingerprint": configuration_fingerprint(configuration),
        "benchmark_version": benchmark_version,
        "seed": seed,
        "runtime_versions": runtime_versions(),
        "code_revision": code_revision(),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
