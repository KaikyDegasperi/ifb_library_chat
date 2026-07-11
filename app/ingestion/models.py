"""Contratos serializáveis produzidos pela ingestão."""

from datetime import datetime

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    document_id: str
    title: str | None
    file_name: str
    file_path: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int
    document_hash: str
    processed_at: datetime


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata


class DocumentResult(BaseModel):
    document_id: str | None
    file_path: str
    status: str
    chunks: int = 0
    document_hash: str | None = None
    output_file: str | None = None
    structured_document_file: str | None = None
    error: str | None = None


class IngestionReport(BaseModel):
    documents_processed: int
    documents_skipped: int
    documents_failed: int
    chunks_created: int
    elapsed_seconds: float
    results: list[DocumentResult]
