import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.api import app
from app.config import Settings
from app.dependencies import (
    provide_document_service,
    provide_rag_service,
    provide_settings,
    provide_vector_service,
)
from app.ingestion.models import DocumentResult, IngestionReport
from app.rag.models import RAGResponse, RAGSource
from app.repositories.models import DocumentRecord
from app.services.documents import DocumentService
from app.vectorstore.models import IndexFileResult, IndexReport, SearchResult


def document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        title="TCC de teste",
        file_name="teste.pdf",
        file_path="/documentos/teste.pdf",
        document_hash="hash-1",
        processed_at="2026-01-01T00:00:00Z",
        chunk_count=2,
        page_start=1,
        page_end=4,
    )


class FakeRepository:
    def __init__(self) -> None:
        self.available = True

    def list(self) -> list[DocumentRecord]:
        return [document()] if self.available else []

    def get(self, document_id: str) -> DocumentRecord | None:
        if self.available and document_id == "doc-1":
            return document()
        return None

    def delete(self, document_id: str) -> int:
        if self.available and document_id == "doc-1":
            self.available = False
            return 2
        return 0


class FakeIngestor:
    def ingest(self, input_path: Path | str) -> IngestionReport:
        return IngestionReport(
            documents_processed=1,
            documents_skipped=0,
            documents_failed=0,
            chunks_created=2,
            elapsed_seconds=0.01,
            results=[
                DocumentResult(
                    document_id="doc-1",
                    file_path=str(input_path),
                    status="processed",
                    chunks=2,
                    document_hash="hash-1",
                    output_file="/tmp/doc-1.chunks.json",
                )
            ],
        )


class FakeVectorService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def index(self, input_path: Path | str) -> IndexReport:
        return IndexReport(
            documents_indexed=1,
            documents_skipped=0,
            documents_failed=0,
            chunks_indexed=2,
            chunks_removed=0,
            elapsed_seconds=0.01,
            collection_count=2,
            results=[
                IndexFileResult(
                    file_path=str(input_path),
                    document_id="doc-1",
                    status="indexed",
                    chunks=2,
                )
            ],
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        title: str | None = None,
    ) -> list[SearchResult]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "document_id": document_id,
                "title": title,
            }
        )
        return [
            SearchResult(
                chunk_id="chunk-1",
                content="Trecho recuperado sobre tecnologia.",
                similarity=0.82,
                document_id="doc-1",
                title="TCC de teste",
                file_name="teste.pdf",
                file_path="/documentos/teste.pdf",
                page_start=3,
                page_end=3,
                section="Tecnologia",
                chunk_index=1,
                document_hash="hash-1",
                processed_at="2026-01-01T00:00:00Z",
            )
        ]


class FakeRAGService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def answer(
        self,
        question: str,
        document_id: str | None = None,
        title: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        self.calls.append(
            {
                "question": question,
                "top_k": top_k,
                "document_id": document_id,
                "title": title,
            }
        )
        return RAGResponse(
            answer="A tecnologia aparece no contexto [Fonte 1].",
            sources=[
                RAGSource(
                    document_id="doc-1",
                    title="TCC de teste",
                    file_name="teste.pdf",
                    page_start=3,
                    page_end=3,
                    section="Tecnologia",
                    chunk_id="chunk-1",
                    score=0.82,
                )
            ],
            retrieval_time_ms=12,
            generation_time_ms=20,
        )


def request(method: str, path: str, **kwargs) -> httpx.Response:
    async def execute() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(execute())


@pytest.fixture
def api_services(tmp_path: Path):
    repository = FakeRepository()
    vector = FakeVectorService()
    document_service = DocumentService(
        repository=repository,
        ingestion_factory=FakeIngestor,
        indexer=vector,
        documents_dir=tmp_path / "documents",
        max_upload_size_bytes=32,
    )
    rag = FakeRAGService()
    settings = Settings(
        documents_dir=tmp_path / "documents",
        processed_dir=tmp_path / "processed",
        chroma_dir=tmp_path / "chroma",
        logs_dir=tmp_path / "logs",
        max_upload_size_mb=1,
    )

    async def override_documents() -> DocumentService:
        return document_service

    async def override_vector() -> FakeVectorService:
        return vector

    async def override_rag() -> FakeRAGService:
        return rag

    async def override_settings() -> Settings:
        return settings

    app.dependency_overrides[provide_document_service] = override_documents
    app.dependency_overrides[provide_vector_service] = override_vector
    app.dependency_overrides[provide_rag_service] = override_rag
    app.dependency_overrides[provide_settings] = override_settings
    yield SimpleNamespace(
        repository=repository,
        vector=vector,
        rag=rag,
        documents_dir=settings.documents_dir,
    )
    app.dependency_overrides.clear()


def test_document_endpoints(api_services) -> None:
    listed = request("GET", "/documents")
    found = request("GET", "/documents/doc-1")
    deleted = request("DELETE", "/documents/doc-1")
    missing = request("GET", "/documents/doc-1")

    assert listed.status_code == 200
    assert listed.json()[0]["chunk_count"] == 2
    assert found.status_code == 200
    assert found.json()["file_name"] == "teste.pdf"
    assert deleted.status_code == 200
    assert deleted.json() == {"document_id": "doc-1", "deleted_chunks": 2}
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Documento não encontrado"


def test_valid_pdf_upload_is_ingested(api_services) -> None:
    response = request(
        "POST",
        "/documents/ingest",
        files={"file": ("novo.pdf", b"%PDF-1.4 fixture", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["document_id"] == "doc-1"
    assert (api_services.documents_dir / "novo.pdf").read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize(
    ("filename", "content", "mime_type", "expected_status"),
    [
        ("malware.exe", b"%PDF-1.4", "application/pdf", 400),
        ("../evil.pdf", b"%PDF-1.4", "application/pdf", 400),
        ("falso.pdf", "não é pdf".encode(), "application/pdf", 400),
        ("texto.pdf", b"%PDF-1.4", "text/plain", 415),
        ("grande.pdf", b"%PDF-" + b"x" * 40, "application/pdf", 413),
    ],
)
def test_invalid_upload_is_rejected(
    api_services,
    filename: str,
    content: bytes,
    mime_type: str,
    expected_status: int,
) -> None:
    response = request(
        "POST",
        "/documents/ingest",
        files={"file": (filename, content, mime_type)},
    )

    assert response.status_code == expected_status
    assert response.json()["detail"]


def test_path_traversal_is_rejected(api_services, tmp_path: Path) -> None:
    (tmp_path / "fora.pdf").write_bytes(b"%PDF-1.4")

    response = request(
        "POST",
        "/documents/ingest",
        data={"path": "../fora.pdf"},
    )

    assert response.status_code == 400
    assert "não é permitido" in response.json()["detail"]


def test_ingest_requires_exactly_one_input(api_services) -> None:
    empty = request("POST", "/documents/ingest")
    both = request(
        "POST",
        "/documents/ingest",
        data={"path": "teste.pdf"},
        files={"file": ("teste.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert empty.status_code == 422
    assert both.status_code == 422


def test_search_endpoint_only_returns_retrieval(api_services) -> None:
    response = request(
        "POST",
        "/search",
        json={"query": "tecnologia no ensino", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["content"].startswith("Trecho recuperado")
    assert payload["results"][0]["score"] == 0.82
    assert "answer" not in payload
    assert api_services.vector.calls[0]["top_k"] == 3


def test_chat_endpoint_returns_answer_sources_and_times(api_services) -> None:
    response = request(
        "POST",
        "/chat",
        json={
            "question": "Quais TCCs discutem tecnologia?",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].endswith("[Fonte 1].")
    assert payload["sources"][0]["file_name"] == "teste.pdf"
    assert payload["sources"][0]["page_start"] == 3
    assert payload["retrieval_time_ms"] == 12
    assert payload["generation_time_ms"] == 20
    assert api_services.rag.calls[0]["top_k"] == 5


@pytest.mark.parametrize("endpoint", ["/search", "/chat"])
def test_invalid_request_body_returns_clear_422(api_services, endpoint: str) -> None:
    field = "query" if endpoint == "/search" else "question"
    response = request("POST", endpoint, json={field: "", "top_k": 0})

    assert response.status_code == 422
    assert response.json()["detail"]


def test_openapi_documents_all_minimum_endpoints(api_services) -> None:
    response = request("GET", "/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert {
        "/health",
        "/documents",
        "/documents/{document_id}",
        "/documents/ingest",
        "/search",
        "/chat",
    }.issubset(schema["paths"])
    chat_schema = schema["components"]["schemas"]["ChatRequest"]
    assert "Quais TCCs" in chat_schema["example"]["question"]
