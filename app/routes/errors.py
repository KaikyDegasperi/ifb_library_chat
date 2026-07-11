from fastapi import HTTPException, status

from app.services.documents import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentTooLargeError,
    InvalidDocumentError,
    UnsupportedMediaTypeError,
)


def document_http_error(error: Exception) -> HTTPException:
    if isinstance(error, DocumentNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, DocumentTooLargeError):
        return HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(error))
    if isinstance(error, UnsupportedMediaTypeError):
        return HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error))
    if isinstance(error, InvalidDocumentError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    if isinstance(error, DocumentProcessingError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro interno")
