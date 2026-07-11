"""Estruturas retornadas pelo serviço RAG."""

from pydantic import BaseModel


class RAGSource(BaseModel):
    document_id: str
    title: str | None
    file_name: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_id: str
    score: float


class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    retrieval_time_ms: int
    generation_time_ms: int
