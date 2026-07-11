from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import Settings
from app.dependencies import provide_document_service, provide_settings
from app.schemas.common import ErrorResponse
from app.schemas.documents import DeleteDocumentResponse, DocumentResponse
from app.services.documents import DocumentService, DocumentServiceError
from app.routes.errors import document_http_error

router = APIRouter(prefix="/documents", tags=["documentos"])
ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="Lista os TCCs indexados",
)
async def list_documents(
    service: DocumentService = Depends(provide_document_service),
) -> list[DocumentResponse]:
    documents = service.list_documents()
    return [DocumentResponse.model_validate(item) for item in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Obtém os metadados de um TCC",
)
async def get_document(
    document_id: str,
    service: DocumentService = Depends(provide_document_service),
) -> DocumentResponse:
    try:
        document = service.get_document(document_id)
    except DocumentServiceError as exc:
        raise document_http_error(exc) from exc
    return DocumentResponse.model_validate(document)


@router.post(
    "/ingest",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Envia ou ingere um PDF permitido",
    description=(
        "Envie `file` como PDF ou informe `path`, relativo ao diretório "
        "DOCUMENTS_DIR. Os campos são mutuamente exclusivos."
    ),
)
async def ingest_document(
    file: Annotated[
        UploadFile | None,
        File(description="PDF acadêmico com MIME type application/pdf"),
    ] = None,
    path: Annotated[
        str | None,
        Form(description="Caminho relativo a DOCUMENTS_DIR, por exemplo trabalho.pdf"),
    ] = None,
    service: DocumentService = Depends(provide_document_service),
    settings: Settings = Depends(provide_settings),
) -> DocumentResponse:
    if (file is None) == (path is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Informe exatamente um entre file e path",
        )
    try:
        if file is not None:
            content = await file.read(settings.max_upload_size_bytes + 1)
            document = service.ingest_upload(
                file.filename or "", file.content_type, content
            )
        else:
            document = service.ingest_existing(path or "")
    except DocumentServiceError as exc:
        raise document_http_error(exc) from exc
    return DocumentResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Remove os vetores de um TCC",
)
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(provide_document_service),
) -> DeleteDocumentResponse:
    try:
        deleted = service.delete_document(document_id)
    except DocumentServiceError as exc:
        raise document_http_error(exc) from exc
    return DeleteDocumentResponse(document_id=document_id, deleted_chunks=deleted)
