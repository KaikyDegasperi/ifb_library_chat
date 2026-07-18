from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings
from app.dependencies import provide_rag_service, provide_settings
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
    settings: Settings = Depends(provide_settings),
) -> ChatResponse:
    if len(request.question) > settings.rag_max_question_chars:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Pergunta excede o limite configurado",
        )
    if request.top_k > settings.api_max_top_k:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "top_k excede o limite configurado",
        )
    if any(
        value is not None and len(value) > settings.api_max_filter_chars
        for value in (request.document_id, request.title)
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Filtro excede o limite configurado",
        )
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
