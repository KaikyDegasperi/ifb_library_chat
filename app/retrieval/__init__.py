"""Recuperadores alternativos usados pelo pipeline RAG."""

from app.retrieval.bm25 import BM25IndexService
from app.retrieval.factory import (
    create_bm25_retriever,
    create_dense_retriever,
    create_retriever,
)

__all__ = [
    "BM25IndexService",
    "create_bm25_retriever",
    "create_dense_retriever",
    "create_retriever",
]
