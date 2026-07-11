from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import provide_rag_service
from app.rag.exceptions import InvalidQuestionError
from app.rag.service import RAGService
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Responde usando apenas os TCCs recuperados",
)
async def chat(
    request: ChatRequest,
    service: RAGService = Depends(provide_rag_service),
) -> ChatResponse:
    try:
        response = service.answer(
            request.question,
            request.document_id,
            request.title,
            request.top_k,
        )
    except InvalidQuestionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ChatResponse.model_validate(response.model_dump())
