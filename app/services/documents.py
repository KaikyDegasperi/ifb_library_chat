"""Casos de uso do catálogo, upload, ingestão e remoção de documentos."""

import os
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from app.ingestion.models import IngestionReport
from app.repositories.documents import DocumentRepository
from app.repositories.models import DocumentRecord
from app.vectorstore.models import IndexReport


class Ingestor(Protocol):
    def ingest(self, input_path: Path | str) -> IngestionReport: ...


class Indexer(Protocol):
    def index(self, input_path: Path | str) -> IndexReport: ...


class DocumentServiceError(Exception):
    pass


class DocumentNotFoundError(DocumentServiceError):
    pass


class InvalidDocumentError(DocumentServiceError):
    pass


class UnsupportedMediaTypeError(DocumentServiceError):
    pass


class DocumentTooLargeError(DocumentServiceError):
    pass


class DocumentProcessingError(DocumentServiceError):
    pass


class DocumentService:
    PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}

    def __init__(
        self,
        repository: DocumentRepository,
        ingestion_factory: Callable[[], Ingestor],
        indexer: Indexer,
        documents_dir: Path,
        max_upload_size_bytes: int,
    ) -> None:
        self.repository = repository
        self.ingestion_factory = ingestion_factory
        self.indexer = indexer
        self.documents_dir = documents_dir.resolve()
        self.max_upload_size_bytes = max_upload_size_bytes

    def list_documents(self) -> list[DocumentRecord]:
        return self.repository.list()

    def get_document(self, document_id: str) -> DocumentRecord:
        document = self.repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError("Documento não encontrado")
        return document

    def delete_document(self, document_id: str) -> int:
        deleted = self.repository.delete(document_id)
        if not deleted:
            raise DocumentNotFoundError("Documento não encontrado")
        return deleted

    def ingest_upload(
        self,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> DocumentRecord:
        safe_name = self._validate_file_name(file_name)
        if content_type not in self.PDF_MIME_TYPES:
            raise UnsupportedMediaTypeError(
                "O upload deve usar o MIME type application/pdf"
            )
        if len(content) > self.max_upload_size_bytes:
            raise DocumentTooLargeError(
                f"O PDF excede o limite de {self.max_upload_size_bytes} bytes"
            )
        if not content.startswith(b"%PDF-"):
            raise InvalidDocumentError("O conteúdo enviado não possui assinatura PDF")

        self.documents_dir.mkdir(parents=True, exist_ok=True)
        target = (self.documents_dir / safe_name).resolve()
        self._ensure_within_documents_dir(target)
        temporary = target.with_suffix(target.suffix + ".uploading")
        temporary.write_bytes(content)
        os.replace(temporary, target)
        return self._process(target)

    def ingest_existing(self, relative_path: str) -> DocumentRecord:
        if not relative_path.strip():
            raise InvalidDocumentError("O caminho do PDF não pode ser vazio")
        requested = Path(relative_path)
        if requested.is_absolute():
            raise InvalidDocumentError("Use um caminho relativo ao diretório permitido")
        target = (self.documents_dir / requested).resolve()
        self._ensure_within_documents_dir(target)
        self._validate_file_name(target.name)
        if not target.is_file():
            raise DocumentNotFoundError("Arquivo permitido não encontrado")
        if target.stat().st_size > self.max_upload_size_bytes:
            raise DocumentTooLargeError(
                f"O PDF excede o limite de {self.max_upload_size_bytes} bytes"
            )
        return self._process(target)

    def _process(self, pdf_path: Path) -> DocumentRecord:
        report = self.ingestion_factory().ingest(pdf_path)
        if report.documents_failed or not report.results:
            detail = report.results[0].error if report.results else "sem resultado"
            raise DocumentProcessingError(f"Falha na ingestão: {detail}")
        ingestion_result = report.results[0]
        if not ingestion_result.output_file:
            raise DocumentProcessingError("A ingestão não produziu chunks")
        index_report = self.indexer.index(ingestion_result.output_file)
        if index_report.documents_failed:
            detail = index_report.results[0].error if index_report.results else "sem resultado"
            raise DocumentProcessingError(f"Falha na indexação: {detail}")
        if not ingestion_result.document_id:
            raise DocumentProcessingError("A ingestão não produziu document_id")
        return self.get_document(ingestion_result.document_id)

    def _validate_file_name(self, file_name: str) -> str:
        normalized = unicodedata.normalize("NFKC", file_name).strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or Path(normalized).name != normalized
            or "/" in normalized
            or "\\" in normalized
            or any(ord(character) < 32 for character in normalized)
        ):
            raise InvalidDocumentError("Nome de arquivo inseguro")
        if Path(normalized).suffix.lower() != ".pdf":
            raise InvalidDocumentError("Somente arquivos com extensão .pdf são aceitos")
        return normalized

    def _ensure_within_documents_dir(self, path: Path) -> None:
        if path.parent != self.documents_dir and self.documents_dir not in path.parents:
            raise InvalidDocumentError("O caminho informado não é permitido")
