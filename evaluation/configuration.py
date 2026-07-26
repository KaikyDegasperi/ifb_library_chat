"""Captura segura das configurações relevantes, sem credenciais."""

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings


def code_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def prompt_version() -> str:
    path = Path("app/rag/prompts.py")
    if not path.is_file():
        return "unknown"
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def safe_settings(settings: Settings) -> dict[str, Any]:
    return {
        "chunk_size": settings.ingest_chunk_size,
        "chunk_overlap": settings.ingest_chunk_overlap,
        "top_k": settings.rag_retrieval_top_k,
        "candidate_pool_size": settings.rag_candidate_pool_size,
        "similarity_threshold": settings.rag_min_similarity,
        "embedding_model": settings.embedding_model,
        "generator_model": settings.llm_model or f"provider:{settings.llm_provider}",
        "prompt_version": prompt_version(),
        "llm_timeout_seconds": settings.llm_timeout_seconds,
        "max_context_chars": settings.rag_max_context_chars,
        "duplicate_threshold": settings.rag_duplicate_threshold,
    }


def frozen_configuration(settings: Settings, benchmark_version: str, seed: int) -> dict[str, Any]:
    return {
        "status": "frozen",
        **safe_settings(settings),
        "benchmark_version": benchmark_version,
        "seed": seed,
        "code_revision": code_revision(),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
