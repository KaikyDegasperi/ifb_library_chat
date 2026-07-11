import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import provide_vector_service
from app.schemas.search import SearchRequest, SearchResponse, SearchResultResponse
from app.vectorstore.service import VectorIndexService

router = APIRouter(tags=["busca"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Executa somente a recuperação semântica",
)
async def search(
    request: SearchRequest,
    service: VectorIndexService = Depends(provide_vector_service),
) -> SearchResponse:
    started = time.perf_counter()
    try:
        results = service.search(
            request.query,
            request.top_k,
            request.document_id,
            request.title,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
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
                file_path=item.file_path,
                page_start=item.page_start,
                page_end=item.page_end,
                section=item.section,
                chunk_index=item.chunk_index,
                document_hash=item.document_hash,
            )
            for item in results
        ],
    )
