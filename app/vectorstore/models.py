"""Contratos da indexação e recuperação."""

from pydantic import BaseModel


class IndexFileResult(BaseModel):
    file_path: str
    document_id: str | None
    status: str
    chunks: int = 0
    removed_chunks: int = 0
    error: str | None = None


class IndexReport(BaseModel):
    documents_indexed: int
    documents_skipped: int
    documents_failed: int
    chunks_indexed: int
    chunks_removed: int
    elapsed_seconds: float
    collection_count: int
    results: list[IndexFileResult]


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    similarity: float
    document_id: str
    title: str | None
    file_name: str
    file_path: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int
    document_hash: str
    processed_at: str
