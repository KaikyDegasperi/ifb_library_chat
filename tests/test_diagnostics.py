import hashlib
import json
from pathlib import Path
from typing import Any

from app.cli.diagnose import build_parser
from app.diagnostics import DiagnosticService


class FakeCollection:
    def __init__(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        self.ids = ids
        self.documents = documents
        self.metadatas = metadatas
        self.embeddings = [[float(index), 1.0] for index in range(len(ids))]
        self.metadata = {"embedding_model": "fake-model"}
        self.mutations = 0

    def count(self) -> int:
        return len(self.ids)

    def get(self, **kwargs: Any) -> dict[str, Any]:
        limit = kwargs.get("limit", len(self.ids))
        include = kwargs.get("include", [])
        response: dict[str, Any] = {"ids": self.ids[:limit]}
        if "documents" in include:
            response["documents"] = self.documents[:limit]
        if "metadatas" in include:
            response["metadatas"] = self.metadatas[:limit]
        if "embeddings" in include:
            response["embeddings"] = self.embeddings[:limit]
        return response

    def query(self, **kwargs: Any) -> dict[str, Any]:
        embedding = kwargs["query_embeddings"][0]
        index = int(embedding[0])
        return {
            "ids": [[self.ids[index]]],
            "metadatas": [[self.metadatas[index]]],
            "distances": [[0.0]],
        }


def _write_pdf(path: Path, marker: bytes) -> str:
    path.write_bytes(b"%PDF-1.4\n" + marker)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifacts(
    processed_dir: Path,
    pdf: Path,
    document_hash: str,
    chunks: list[dict[str, Any]],
) -> None:
    document_id = document_hash[:16]
    (processed_dir / f"{document_id}.docling.json").write_text(
        json.dumps({"schema_name": "DoclingDocument", "pages": {"1": {}, "2": {}}}),
        encoding="utf-8",
    )
    payload = {
        "document_id": document_id,
        "document_hash": document_hash,
        "chunks": [],
    }
    for index, values in enumerate(chunks):
        payload["chunks"].append(
            {
                "text": values.pop("text"),
                "metadata": {
                    "document_id": document_id,
                    "title": values.pop("title", "TCC fictício"),
                    "author": values.pop("author", "Pessoa Autora"),
                    "advisor": values.pop("advisor", "Pessoa Orientadora"),
                    "coadvisor": None,
                    "year": values.pop("year", 2026),
                    "file_name": pdf.name,
                    "file_path": str(pdf.resolve()),
                    "page_start": values.pop("page_start", 1),
                    "page_end": values.pop("page_end", 1),
                    "section": "Seção fictícia",
                    "chunk_index": index,
                    "document_hash": document_hash,
                    "processed_at": "2026-01-01T00:00:00Z",
                },
            }
        )
    (processed_dir / f"{document_id}.chunks.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_diagnostic_reports_full_collection_integrity(tmp_path: Path) -> None:
    documents_dir = tmp_path / "pdfs"
    processed_dir = tmp_path / "processed"
    chroma_dir = tmp_path / "chroma"
    documents_dir.mkdir()
    processed_dir.mkdir()
    chroma_dir.mkdir()
    first_pdf = documents_dir / "a.pdf"
    duplicate_pdf = documents_dir / "a-copia.pdf"
    second_pdf = documents_dir / "b.pdf"
    first_hash = _write_pdf(first_pdf, b"mesmo-conteudo")
    _write_pdf(duplicate_pdf, b"mesmo-conteudo")
    second_hash = _write_pdf(second_pdf, b"outro-conteudo")
    _write_artifacts(
        processed_dir,
        first_pdf,
        first_hash,
        [{"text": "chunk válido"}, {"text": "   "}],
    )
    _write_artifacts(
        processed_dir,
        second_pdf,
        second_hash,
        [
            {
                "text": "outro chunk",
                "title": None,
                "author": None,
                "advisor": None,
                "year": None,
                "page_start": None,
                "page_end": None,
            }
        ],
    )
    metadatas = [
        {
            "document_id": first_hash[:16],
            "document_hash": first_hash,
            "file_name": first_pdf.name,
            "file_path": str(first_pdf),
            "page_start": 1,
            "page_end": 1,
        },
        {
            "document_id": second_hash[:16],
            "document_hash": second_hash,
            "file_name": second_pdf.name,
            "file_path": str(second_pdf),
            "page_start": None,
            "page_end": None,
        },
    ]
    collection = FakeCollection(
        ["chunk-1", "chunk-2"],
        ["conteúdo indexado", ""],
        metadatas,
    )

    report = DiagnosticService(
        documents_dir=documents_dir,
        processed_dir=processed_dir,
        chroma_dir=chroma_dir,
        chroma_collection="teste",
        embedding_model="fake-model",
        collection=collection,
        technical_probe_count=2,
    ).run()

    assert report.total_pdfs == 3
    assert report.status == "issues"
    assert report.unique_pdf_hashes == 2
    assert report.total_processed == 2
    assert report.total_with_chunks == 2
    assert report.total_indexed == 2
    assert report.total_chunks == 3
    assert report.average_chunks_per_document == 1.5
    assert report.median_chunks_per_document == 1.5
    assert {item.document_hash for item in report.documents} == {
        first_hash,
        second_hash,
    }
    assert all(item.processed_by_docling for item in report.documents)
    assert all(item.has_chunks for item in report.documents)
    assert all(item.indexed_in_chromadb for item in report.documents)
    assert report.duplicates[0].document_hash == first_hash
    assert len(report.duplicates[0].files) == 2
    assert report.empty_chunks[0].document_id == first_hash[:16]
    assert report.missing_metadata[0].fields == [
        "title",
        "author",
        "year",
        "advisor",
    ]
    assert report.documents_without_indexed_pages == [second_hash]
    assert report.chromadb_integrity.empty_indexed_chunks == ["chunk-2"]
    assert report.chromadb_integrity.technical_probes[0].status == "ok"
    assert report.chromadb_integrity.technical_probes[1].status == "error"
    assert report.chromadb_integrity.source_errors[0].code == "source_page_missing"
    assert report.configuration.read_only is True
    assert collection.mutations == 0


def test_diagnostic_reports_missing_artifacts_and_database(tmp_path: Path) -> None:
    documents_dir = tmp_path / "pdfs"
    documents_dir.mkdir()
    _write_pdf(documents_dir / "sem-artefatos.pdf", b"fixture")

    report = DiagnosticService(
        documents_dir=documents_dir,
        processed_dir=tmp_path / "processed",
        chroma_dir=tmp_path / "chroma",
        chroma_collection="ausente",
        embedding_model="fake-model",
        collection=None,
        collection_error="coleção ausente",
    ).run()

    assert report.total_pdfs == 1
    assert report.status == "issues"
    assert report.total_processed == 0
    assert report.total_with_chunks == 0
    assert report.total_indexed == 0
    assert report.total_chunks == 0
    assert {issue.code for issue in report.documents_with_errors} == {
        "missing_docling_artifact",
        "missing_chunks_artifact",
    }
    assert report.chromadb_integrity.available is False
    assert report.chromadb_integrity.error == "coleção ausente"


def test_diagnostic_is_ok_when_every_layer_is_consistent(tmp_path: Path) -> None:
    documents_dir = tmp_path / "pdfs"
    processed_dir = tmp_path / "processed"
    chroma_dir = tmp_path / "chroma"
    documents_dir.mkdir()
    processed_dir.mkdir()
    chroma_dir.mkdir()
    pdf = documents_dir / "completo.pdf"
    document_hash = _write_pdf(pdf, b"completo")
    _write_artifacts(
        processed_dir,
        pdf,
        document_hash,
        [{"text": "chunk completo", "page_start": 1, "page_end": 1}],
    )
    collection = FakeCollection(
        ["chunk-completo"],
        ["chunk completo"],
        [
            {
                "document_id": document_hash[:16],
                "document_hash": document_hash,
                "file_name": pdf.name,
                "file_path": str(pdf),
                "page_start": 1,
                "page_end": 1,
            }
        ],
    )

    report = DiagnosticService(
        documents_dir=documents_dir,
        processed_dir=processed_dir,
        chroma_dir=chroma_dir,
        chroma_collection="teste",
        embedding_model="fake-model",
        collection=collection,
        technical_probe_count=1,
    ).run()

    assert report.status == "ok"
    assert report.chromadb_integrity.technical_probes[0].status == "ok"


def test_reindex_requires_explicit_command_line_option() -> None:
    parser = build_parser()

    default_args = parser.parse_args([])
    explicit_args = parser.parse_args(["--reindex"])

    assert default_args.reindex is False
    assert explicit_args.reindex is True
