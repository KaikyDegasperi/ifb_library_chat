"""Recuperadores alternativos usados pelo pipeline RAG."""

from app.retrieval.bm25 import BM25IndexService

__all__ = ["BM25IndexService"]
