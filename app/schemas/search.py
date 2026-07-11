from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Quais trabalhos discutem discalculia?",
                "top_k": 5,
                "document_id": None,
                "title": None,
            }
        }
    )

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: str | None = None
    title: str | None = None


class SearchResultResponse(BaseModel):
    chunk_id: str
    content: str
    score: float
    document_id: str
    title: str | None
    file_name: str
    file_path: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int
    document_hash: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]
    retrieval_time_ms: int
