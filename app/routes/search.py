import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings
from app.dependencies import provide_settings, provide_vector_service
from app.schemas.search import SearchRequest, SearchResponse, SearchResultResponse
from app.vectorstore.service import VectorIndexService

router = APIRouter(tags=["busca"])
logger = logging.getLogger(__name__)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Executa somente a recuperação semântica",
)
async def search(
    request: SearchRequest,
    service: VectorIndexService = Depends(provide_vector_service),
    settings: Settings = Depends(provide_settings),
) -> SearchResponse:
    if len(request.query) > settings.search_max_query_chars:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Consulta excede o limite configurado",
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
    started = time.perf_counter()
    try:
        results = service.search(
            request.query,
            request.top_k,
            request.document_id,
            request.title,
        )
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Consulta inválida",
        ) from exc
    except Exception as exc:
        logger.error("Busca vetorial indisponível: %s", type(exc).__name__)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Busca temporariamente indisponível",
        ) from exc
    return SearchResponse(
        query=request.query,
        retrieval_time_ms=round((time.perf_counter() - started) * 1000),
        results=[
            SearchResultResponse(
                chunk_id=item.chunk_id,
                content=item.content,
                score=item.similarity,
                document_id=item.document_id,
                title=item.title,
                file_name=item.file_name,
                page_start=item.page_start,
                page_end=item.page_end,
                section=item.section,
                chunk_index=item.chunk_index,
                document_hash=item.document_hash,
            )
            for item in results
        ],
    )
