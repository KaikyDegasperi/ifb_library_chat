from pathlib import Path

import pytest

from app.ingestion.models import DocumentResult, IngestionReport
from app.services.documents import (
    DocumentProcessingError,
    DocumentService,
    InvalidDocumentError,
)


class FailingIngestor:
    def ingest(self, input_path: Path | str) -> IngestionReport:
        return IngestionReport(
            documents_processed=0,
            documents_skipped=0,
            documents_failed=1,
            chunks_created=0,
            elapsed_seconds=0.0,
            results=[
                DocumentResult(
                    document_id=None,
                    file_path=str(input_path),
                    status="error",
                    error="internal-secret-path-and-provider-detail",
                )
            ],
        )


class DeleteOnlyRepository:
    def list(self):
        return []

    def get(self, document_id: str):
        return None

    def delete(self, document_id: str) -> int:
        return 2 if document_id == "doc-1" else 0


def make_service(tmp_path: Path, max_name_chars: int = 180) -> DocumentService:
    return DocumentService(
        repository=DeleteOnlyRepository(),
        ingestion_factory=FailingIngestor,
        indexer=object(),
        documents_dir=tmp_path / "documents",
        max_upload_size_bytes=1024,
        max_upload_filename_chars=max_name_chars,
    )


def test_upload_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.documents_dir.mkdir()
    existing = service.documents_dir / "trabalho.pdf"
    existing.write_bytes(b"%PDF-1.4\noriginal")

    with pytest.raises(InvalidDocumentError, match="esse nome"):
        service.ingest_upload(
            "trabalho.pdf",
            "application/pdf",
            "%PDF-1.4\nnovo conteúdo".encode(),
        )

    assert existing.read_bytes() == b"%PDF-1.4\noriginal"


def test_identical_upload_reuses_existing_file_for_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_service(tmp_path)
    service.documents_dir.mkdir()
    existing = service.documents_dir / "trabalho.pdf"
    content = "%PDF-1.4\nconteúdo idêntico".encode()
    existing.write_bytes(content)
    processed: list[Path] = []

    def process(path: Path) -> Path:
        processed.append(path)
        return path

    monkeypatch.setattr(service, "_process", process)

    result = service.ingest_upload(
        "trabalho.pdf",
        "application/pdf",
        content,
    )

    assert result == existing
    assert processed == [existing]
    assert existing.read_bytes() == content


def test_upload_rejects_duplicate_content_under_another_name(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.documents_dir.mkdir()
    content = "%PDF-1.4\nmesmo conteúdo".encode()
    (service.documents_dir / "original.pdf").write_bytes(content)

    with pytest.raises(InvalidDocumentError, match="já existe no acervo"):
        service.ingest_upload("copia.pdf", "application/pdf", content)

    assert not (service.documents_dir / "copia.pdf").exists()


def test_temporary_upload_is_removed_and_internal_error_is_hidden(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path)

    with pytest.raises(DocumentProcessingError) as error:
        service.ingest_upload(
            "falha.pdf",
            "application/pdf",
            b"%PDF-1.4\nfixture",
        )

    assert "internal-secret" not in str(error.value)
    assert not list(service.documents_dir.glob(".upload-*.tmp"))


def test_existing_file_revalidates_pdf_signature(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.documents_dir.mkdir()
    (service.documents_dir / "falso.pdf").write_text(
        "conteúdo que não é PDF",
        encoding="utf-8",
    )

    with pytest.raises(InvalidDocumentError, match="assinatura PDF"):
        service.ingest_existing("falso.pdf")


def test_file_name_limit_is_configurable(tmp_path: Path) -> None:
    service = make_service(tmp_path, max_name_chars=20)

    with pytest.raises(InvalidDocumentError, match="limite configurado"):
        service.ingest_upload(
            f"{'a' * 30}.pdf",
            "application/pdf",
            b"%PDF-1.4",
        )


def test_deletion_removes_only_index_entries(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.documents_dir.mkdir()
    pdf = service.documents_dir / "preservado.pdf"
    pdf.write_bytes(b"%PDF-1.4\nfixture")

    deleted = service.delete_document("doc-1")

    assert deleted == 2
    assert pdf.is_file()


def test_document_preview_resolves_only_catalogued_pdf(tmp_path: Path) -> None:
    class PreviewRepository(DeleteOnlyRepository):
        def get(self, document_id: str):
            if document_id != "doc-1":
                return None
            from app.repositories.models import DocumentRecord

            return DocumentRecord(
                document_id="doc-1",
                title="TCC",
                file_name="trabalho.pdf",
                file_path="/caminho/interno/ignorado.pdf",
                document_hash="hash",
                processed_at="2026-01-01T00:00:00Z",
                chunk_count=1,
                page_start=1,
                page_end=2,
            )

    service = make_service(tmp_path)
    service.repository = PreviewRepository()
    service.documents_dir.mkdir()
    expected = service.documents_dir / "trabalho.pdf"
    expected.write_bytes(b"%PDF-1.4\nfixture")

    assert service.get_document_file("doc-1") == expected.resolve()
