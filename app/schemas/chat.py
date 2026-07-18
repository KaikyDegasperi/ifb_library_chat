from pydantic import BaseModel, ConfigDict, Field

from app.rag.models import RAGSource


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": (
                    "Quais TCCs discutem o uso de tecnologia no ensino de matemática?"
                ),
                "top_k": 5,
            }
        }
    )

    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)
    document_id: str | None = None
    title: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    retrieval_time_ms: int
    generation_time_ms: int
