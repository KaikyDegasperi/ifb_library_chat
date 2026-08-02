"""Captura reproduzível da configuração efetivamente usada pelo RAG."""

import hashlib
import json
from pathlib import Path
from typing import Any

from app.config import Settings


def prompt_version() -> str:
    path = Path(__file__).with_name("rag") / "prompts.py"
    if not path.is_file():
        return "unknown"
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def corpus_fingerprint(processed_dir: Path) -> dict[str, Any]:
    """Identifica exatamente os artefatos de chunks usados pelo recuperador."""
    digest = hashlib.sha256()
    document_ids: set[str] = set()
    chunk_count = 0
    files = sorted(processed_dir.glob("*.chunks.json"))
    for path in files:
        content = path.read_bytes()
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
        payload = json.loads(content)
        document_id = str(payload.get("document_id") or "")
        if document_id:
            document_ids.add(document_id)
        chunk_count += len(payload.get("chunks", []))
    return {
        "sha256": digest.hexdigest(),
        "artifact_count": len(files),
        "document_count": len(document_ids),
        "chunk_count": chunk_count,
    }


def runtime_configuration(settings: Settings) -> dict[str, Any]:
    """Retorna somente parâmetros técnicos seguros, sem credenciais."""
    return {
        "chunk_size": settings.ingest_chunk_size,
        "chunk_overlap": settings.ingest_chunk_overlap,
        "retrieval_provider": settings.retrieval_provider,
        "bm25_k1": settings.bm25_k1,
        "bm25_b": settings.bm25_b,
        "embedding_model": settings.embedding_model,
        "top_k": settings.rag_retrieval_top_k,
        "candidate_pool_size": settings.rag_candidate_pool_size,
        "relevance_threshold": settings.rag_min_similarity,
        "duplicate_threshold": settings.rag_duplicate_threshold,
        "max_context_chars": settings.rag_max_context_chars,
        "llm_provider": settings.llm_provider,
        "generator_model": settings.llm_model or f"provider:{settings.llm_provider}",
        "llm_temperature": settings.llm_temperature,
        "llm_top_p": settings.llm_top_p,
        "llm_max_tokens": settings.llm_max_tokens,
        "llm_timeout_seconds": settings.llm_timeout_seconds,
        "prompt_version": prompt_version(),
        "corpus": corpus_fingerprint(settings.processed_dir),
    }
