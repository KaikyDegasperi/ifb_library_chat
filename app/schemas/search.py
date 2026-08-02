from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Quais trabalhos discutem discalculia?",
                "document_id": None,
                "title": None,
            }
        }
    )

    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1)
    document_id: str | None = None
    title: str | None = None


class SearchResultResponse(BaseModel):
    chunk_id: str
    content: str
    score: float
    document_id: str
    title: str | None
    file_name: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int
    document_hash: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]
    retrieval_time_ms: int
