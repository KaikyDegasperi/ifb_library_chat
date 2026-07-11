from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    chroma: dict[str, Any]
    embeddings: dict[str, Any]
    llm: dict[str, Any]
