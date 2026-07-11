"""Verificações dos componentes usados pela aplicação."""

import importlib.util
import logging
from typing import Any

import chromadb

from app.config import Settings

logger = logging.getLogger(__name__)


def check_chroma(settings: Settings) -> dict[str, Any]:
    try:
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        heartbeat = client.heartbeat()
        return {"available": True, "heartbeat": heartbeat}
    except Exception as exc:  # pragma: no cover - depende do armazenamento
        logger.exception("Falha ao verificar ChromaDB")
        return {"available": False, "detail": type(exc).__name__}


def check_embeddings(settings: Settings) -> dict[str, Any]:
    package_available = importlib.util.find_spec("sentence_transformers") is not None
    configured = bool(settings.embedding_model.strip())
    return {
        "available": package_available and configured,
        "model": settings.embedding_model,
        "detail": (
            "package_and_model_configured"
            if package_available and configured
            else "package_or_model_missing"
        ),
    }


def check_llm(settings: Settings) -> dict[str, Any]:
    provider = settings.llm_provider.strip().lower()
    if provider == "none":
        return {
            "available": False,
            "provider": "none",
            "detail": "not_configured",
        }

    available = bool(provider and settings.llm_model and settings.llm_base_url)
    return {
        "available": available,
        "provider": provider,
        "model": settings.llm_model,
        "detail": "configured" if available else "incomplete_configuration",
    }


def build_health(settings: Settings) -> dict[str, Any]:
    chroma = check_chroma(settings)
    embeddings = check_embeddings(settings)
    llm = check_llm(settings)
    essentials_available = chroma["available"] and embeddings["available"]
    return {
        "status": "ok" if essentials_available else "degraded",
        "chroma": chroma,
        "embeddings": embeddings,
        "llm": llm,
    }
