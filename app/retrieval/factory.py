"""Fábrica única dos recuperadores usados pela aplicação e pelos CLIs."""

from app.config import Settings
from app.rag.service import Retriever
from app.retrieval.bm25 import BM25IndexService
from app.vectorstore.embeddings import SentenceTransformerProvider
from app.vectorstore.service import VectorIndexService


def create_dense_retriever(settings: Settings) -> VectorIndexService:
    return VectorIndexService(
        persist_dir=settings.chroma_dir,
        collection_name=settings.chroma_collection,
        embedding_provider=SentenceTransformerProvider(
            settings.embedding_model,
            settings.embedding_batch_size,
        ),
        batch_size=settings.embedding_batch_size,
    )


def create_bm25_retriever(
    settings: Settings,
    *,
    active_document_ids: set[str] | None = None,
) -> BM25IndexService:
    service = BM25IndexService(
        settings.processed_dir,
        k1=settings.bm25_k1,
        b=settings.bm25_b,
    )
    service.index(
        settings.processed_dir,
        allowed_document_ids=active_document_ids,
    )
    return service


def create_retriever(
    settings: Settings,
    *,
    active_document_ids: set[str] | None = None,
) -> Retriever:
    if settings.retrieval_provider == "bm25":
        return create_bm25_retriever(
            settings,
            active_document_ids=active_document_ids,
        )
    return create_dense_retriever(settings)
