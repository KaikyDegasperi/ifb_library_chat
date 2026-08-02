"""Composição e injeção das dependências da API."""

import secrets
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.ingestion.service import IngestionService
from app.rag.factory import create_rag_service
from app.rag.service import RAGService, Retriever
from app.retrieval import (
    BM25IndexService,
    create_bm25_retriever,
    create_dense_retriever,
)
from app.repositories.documents import ChromaDocumentRepository
from app.services.documents import DocumentService
from app.vectorstore.service import VectorIndexService


async def provide_settings() -> Settings:
    return get_settings()


_admin_bearer = HTTPBearer(auto_error=False)


async def require_admin(
    settings: Settings = Depends(provide_settings),
    credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer),
) -> None:
    """Autoriza uma operação administrativa sem expor a credencial."""
    expected = settings.admin_token_value
    if expected is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Operações administrativas estão desabilitadas",
        )

    provided = (
        credentials.credentials
        if credentials is not None and credentials.scheme.casefold() == "bearer"
        else None
    )
    if provided is None or not secrets.compare_digest(
        provided.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciais administrativas inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


@lru_cache
def _dense_service() -> VectorIndexService:
    return create_dense_retriever(get_settings())


@lru_cache
def _bm25_service() -> BM25IndexService:
    settings = get_settings()
    repository = ChromaDocumentRepository(_dense_service().collection)
    active_document_ids = {item.document_id for item in repository.list()}
    return create_bm25_retriever(
        settings,
        active_document_ids=active_document_ids,
    )


@lru_cache
def _retrieval_service() -> Retriever:
    settings = get_settings()
    if settings.retrieval_provider == "bm25":
        return _bm25_service()
    return _dense_service()


async def provide_vector_service() -> Retriever:
    """Mantém o nome público antigo, retornando o recuperador configurado."""
    return _retrieval_service()


@lru_cache
def _document_service() -> DocumentService:
    settings = get_settings()
    vector_service = _dense_service()
    repository = ChromaDocumentRepository(vector_service.collection)
    return DocumentService(
        repository=repository,
        ingestion_factory=lambda: IngestionService(
            output_dir=settings.processed_dir,
            chunk_size=settings.ingest_chunk_size,
            chunk_overlap=settings.ingest_chunk_overlap,
            device=settings.ingest_device,
            embedding_model=settings.embedding_model,
        ),
        indexer=vector_service,
        secondary_indexer=_bm25_service(),
        documents_dir=settings.documents_dir,
        max_upload_size_bytes=settings.max_upload_size_bytes,
        max_upload_filename_chars=settings.max_upload_filename_chars,
    )


async def provide_document_service() -> DocumentService:
    return _document_service()


@lru_cache
def _rag_service() -> RAGService:
    return create_rag_service(
        get_settings(),
        retriever=_retrieval_service(),
    )


async def provide_rag_service() -> RAGService:
    return _rag_service()
