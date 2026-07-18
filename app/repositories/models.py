"""Modelos internos retornados pelos repositórios."""

from pydantic import BaseModel


class DocumentRecord(BaseModel):
    document_id: str
    title: str | None
    author: str | None = None
    advisor: str | None = None
    coadvisor: str | None = None
    year: int | None = None
    file_name: str
    file_path: str
    document_hash: str
    processed_at: str
    chunk_count: int
    page_start: int | None
    page_end: int | None
