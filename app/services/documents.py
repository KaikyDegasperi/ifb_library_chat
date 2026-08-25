"""Casos de uso do catálogo, upload, ingestão e remoção de documentos."""

import hashlib
import os
import tempfile
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


class SecondaryIndexer(Indexer, Protocol):
    def delete(self, document_id: str) -> int: ...


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
        max_upload_filename_chars: int = 180,
        secondary_indexer: SecondaryIndexer | None = None,
    ) -> None:
        self.repository = repository
        self.ingestion_factory = ingestion_factory
        self.indexer = indexer
        self.secondary_indexer = secondary_indexer
        self.documents_dir = documents_dir.resolve()
        self.max_upload_size_bytes = max_upload_size_bytes
        self.max_upload_filename_chars = max_upload_filename_chars

    def list_documents(self) -> list[DocumentRecord]:
        return self.repository.list()

    def get_document(self, document_id: str) -> DocumentRecord:
        document = self.repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError("Documento não encontrado")
        return document

    def get_document_file(self, document_id: str) -> Path:
        document = self.get_document(document_id)
        target = (self.documents_dir / document.file_name).resolve()
        self._ensure_within_documents_dir(target)
        if not target.is_file():
            raise DocumentNotFoundError("Arquivo PDF não encontrado")
        if target.suffix.casefold() != ".pdf" or not self._has_pdf_signature(target):
            raise InvalidDocumentError("O arquivo catalogado não é um PDF válido")
        return target

    def delete_document(self, document_id: str) -> int:
        deleted = self.repository.delete(document_id)
        if not deleted:
            raise DocumentNotFoundError("Documento não encontrado")
        if self.secondary_indexer is not None:
            self.secondary_indexer.delete(document_id)
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
        incoming_hash = hashlib.sha256(content).hexdigest()
        if target.exists():
            try:
                existing_hash = self._sha256(target)
            except OSError as exc:
                raise DocumentProcessingError(
                    "Não foi possível verificar o PDF existente"
                ) from exc
            if existing_hash == incoming_hash:
                return self._process(target)
            raise InvalidDocumentError(
                "Já existe um PDF diferente com esse nome"
            )
        if self._duplicate_file(incoming_hash) is not None:
            raise InvalidDocumentError("Este PDF já existe no acervo")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".upload-",
            suffix=".tmp",
            dir=self.documents_dir,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError as exc:
                raise InvalidDocumentError(
                    "Já existe um PDF com esse nome"
                ) from exc
            except OSError as exc:
                raise DocumentProcessingError(
                    "Não foi possível armazenar o PDF"
                ) from exc
        finally:
            temporary.unlink(missing_ok=True)
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
        if not self._has_pdf_signature(target):
            raise InvalidDocumentError("O arquivo não possui assinatura PDF")
        return self._process(target)

    def _process(self, pdf_path: Path) -> DocumentRecord:
        report = self.ingestion_factory().ingest(pdf_path)
        if report.documents_failed or not report.results:
            raise DocumentProcessingError("Não foi possível processar o PDF")
        ingestion_result = report.results[0]
        if not ingestion_result.output_file:
            raise DocumentProcessingError("A ingestão não produziu chunks")
        index_report = self.indexer.index(ingestion_result.output_file)
        if index_report.documents_failed:
            raise DocumentProcessingError("Não foi possível indexar o PDF")
        if self.secondary_indexer is not None:
            secondary_report = self.secondary_indexer.index(
                ingestion_result.output_file
            )
            if secondary_report.documents_failed:
                raise DocumentProcessingError(
                    "Não foi possível atualizar o índice lexical"
                )
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
        if len(normalized) > self.max_upload_filename_chars:
            raise InvalidDocumentError("Nome de arquivo excede o limite configurado")
        if Path(normalized).suffix.lower() != ".pdf":
            raise InvalidDocumentError("Somente arquivos com extensão .pdf são aceitos")
        return normalized

    def _ensure_within_documents_dir(self, path: Path) -> None:
        if path.parent != self.documents_dir and self.documents_dir not in path.parents:
            raise InvalidDocumentError("O caminho informado não é permitido")

    def _duplicate_file(self, expected_hash: str) -> Path | None:
        for existing in self.documents_dir.iterdir():
            if not existing.is_file() or existing.suffix.lower() != ".pdf":
                continue
            try:
                if self._sha256(existing) == expected_hash:
                    return existing
            except OSError as exc:
                raise DocumentProcessingError(
                    "Não foi possível verificar duplicidade do PDF"
                ) from exc
        return None

    @staticmethod
    def _has_pdf_signature(path: Path) -> bool:
        with path.open("rb") as file:
            return file.read(5) == b"%PDF-"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
