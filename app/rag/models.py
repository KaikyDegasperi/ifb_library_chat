"""Estruturas retornadas pelo serviço RAG."""

from pydantic import BaseModel, Field


class RAGSource(BaseModel):
    document_id: str
    title: str | None
    file_name: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_id: str
    score: float


class RAGTimings(BaseModel):
    embedding_time_ms: int = 0
    vector_search_time_ms: int = 0
    context_preparation_time_ms: int = 0
    generation_time_ms: int = 0
    total_time_ms: int = 0


class RAGObservation(BaseModel):
    request_id: str
    status: str
    source_count: int
    context_chars: int
    error_type: str | None = None
    timings: RAGTimings


class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    retrieval_time_ms: int
    generation_time_ms: int
    observation: RAGObservation | None = Field(default=None, exclude=True)
