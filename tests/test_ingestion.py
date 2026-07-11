import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ingestion.service import IngestionService


class FakeDocument:
    def __init__(self, title: str = "Um TCC de teste") -> None:
        self.texts = [
            SimpleNamespace(label=SimpleNamespace(value="title"), text=title)
        ]

    def save_as_json(self, path: Path) -> None:
        path.write_text('{"schema_name":"DoclingDocument"}', encoding="utf-8")


class FakeConverter:
    def __init__(self) -> None:
        self.calls = 0

    def convert(self, path: Path, raises_on_error: bool = True) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(document=FakeDocument(title=f"Título de {path.stem}"))


class FakeChunker:
    def chunk(self, dl_doc: FakeDocument):
        provenance = SimpleNamespace(page_no=2)
        item = SimpleNamespace(prov=[provenance])
        meta = SimpleNamespace(
            headings=["Introdução"],
            doc_items=[item],
        )
        yield SimpleNamespace(
            text="Texto acadêmico de teste.",
            meta=meta,
        )

    def contextualize(self, chunk: SimpleNamespace) -> str:
        return f"# {chunk.meta.headings[0]}\n\n{chunk.text}"


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "trabalho.pdf"
    path.write_bytes(b"%PDF-1.4\nfixture pequena")
    return path


@pytest.fixture
def service(tmp_path: Path) -> IngestionService:
    return IngestionService(
        output_dir=tmp_path / "processed",
        chunk_size=50,
        chunk_overlap=10,
        converter=FakeConverter(),
        chunker=FakeChunker(),
    )


def test_valid_file_generates_chunks(
    service: IngestionService,
    valid_pdf: Path,
) -> None:
    report = service.ingest(valid_pdf)

    assert report.documents_processed == 1
    assert report.documents_failed == 0
    assert report.chunks_created == 1
    assert Path(report.results[0].output_file or "").is_file()
    assert Path(report.results[0].structured_document_file or "").is_file()


def test_missing_file_raises_clear_error(service: IngestionService) -> None:
    with pytest.raises(FileNotFoundError, match="entrada inexistente"):
        service.ingest("nao-existe.pdf")


def test_invalid_pdf_is_reported_without_conversion(
    service: IngestionService,
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "invalido.pdf"
    invalid.write_text("isto não é um PDF", encoding="utf-8")

    report = service.ingest(invalid)

    assert report.documents_failed == 1
    assert report.documents_processed == 0
    assert "assinatura PDF" in (report.results[0].error or "")


def test_directory_continues_after_invalid_document(
    service: IngestionService,
    tmp_path: Path,
) -> None:
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4\nprimeiro")
    (tmp_path / "b.pdf").write_text("inválido", encoding="utf-8")
    (tmp_path / "c.PDF").write_bytes(b"%PDF-1.4\nterceiro")
    (tmp_path / "ignorar.txt").write_text("fora do lote", encoding="utf-8")

    report = service.ingest(tmp_path)

    assert report.documents_processed == 2
    assert report.documents_failed == 1
    assert report.chunks_created == 2
    assert len(report.results) == 3


def test_unchanged_file_is_not_reprocessed(
    service: IngestionService,
    valid_pdf: Path,
) -> None:
    first = service.ingest(valid_pdf)
    second = service.ingest(valid_pdf)

    assert first.documents_processed == 1
    assert second.documents_processed == 0
    assert second.documents_skipped == 1
    assert service.converter.calls == 1


def test_chunk_metadata_is_traceable(
    service: IngestionService,
    valid_pdf: Path,
) -> None:
    report = service.ingest(valid_pdf)
    output_path = Path(report.results[0].output_file or "")
    chunk = json.loads(output_path.read_text(encoding="utf-8"))["chunks"][0]
    metadata = chunk["metadata"]

    assert chunk["text"].startswith("# Introdução")
    assert metadata["document_id"] == metadata["document_hash"][:16]
    assert metadata["title"] == "Título de trabalho"
    assert metadata["file_name"] == "trabalho.pdf"
    assert metadata["file_path"] == str(valid_pdf.resolve())
    assert metadata["page_start"] == 2
    assert metadata["page_end"] == 2
    assert metadata["section"] == "Introdução"
    assert metadata["chunk_index"] == 0
    assert metadata["processed_at"]
