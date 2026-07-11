"""Composição e injeção das dependências da API."""

from functools import lru_cache

from app.config import Settings, get_settings
from app.ingestion.service import IngestionService
from app.rag.factory import create_rag_service
from app.rag.service import RAGService
from app.repositories.documents import ChromaDocumentRepository
from app.services.documents import DocumentService
from app.vectorstore.embeddings import SentenceTransformerProvider
from app.vectorstore.service import VectorIndexService


async def provide_settings() -> Settings:
    return get_settings()


@lru_cache
def _vector_service() -> VectorIndexService:
    settings = get_settings()
    return VectorIndexService(
        persist_dir=settings.chroma_dir,
        collection_name=settings.chroma_collection,
        embedding_provider=SentenceTransformerProvider(
            settings.embedding_model,
            settings.embedding_batch_size,
        ),
        batch_size=settings.embedding_batch_size,
    )


async def provide_vector_service() -> VectorIndexService:
    return _vector_service()


@lru_cache
def _document_service() -> DocumentService:
    settings = get_settings()
    vector_service = _vector_service()
    repository = ChromaDocumentRepository(vector_service.collection)
    return DocumentService(
        repository=repository,
        ingestion_factory=lambda: IngestionService(
            output_dir=settings.processed_dir,
            chunk_size=settings.ingest_chunk_size,
            chunk_overlap=settings.ingest_chunk_overlap,
            device=settings.ingest_device,
        ),
        indexer=vector_service,
        documents_dir=settings.documents_dir,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


async def provide_document_service() -> DocumentService:
    return _document_service()


@lru_cache
def _rag_service() -> RAGService:
    return create_rag_service(get_settings())


async def provide_rag_service() -> RAGService:
    return _rag_service()
