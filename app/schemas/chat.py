from pydantic import BaseModel, ConfigDict, Field

from app.rag.models import RAGSource, SelectionTrace


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": (
                    "Quais TCCs discutem o uso de tecnologia no ensino de matemática?"
                ),
            }
        }
    )

    question: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1)
    document_id: str | None = None
    title: str | None = None
    assistive_query_handling: bool = False


class ChatResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    retrieved_context: list[RAGSource]
    selection_trace: list[SelectionTrace]
    retrieval_time_ms: int
    generation_time_ms: int
