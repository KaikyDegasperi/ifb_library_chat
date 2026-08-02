from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    retrieval: dict[str, Any]
    configuration: dict[str, Any]
    chroma: dict[str, Any]
    embeddings: dict[str, Any]
    llm: dict[str, Any]
