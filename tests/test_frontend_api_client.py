import json

import httpx
import pytest

from frontend.api_client import (
    APIClient,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
)


def json_response(
    payload: object,
    status_code: int = 200,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        content=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )


def test_client_uses_real_health_and_documents_contracts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return json_response({"status": "ok", "chroma": {}, "embeddings": {}, "llm": {}})
        if request.url.path == "/documents":
            return json_response([{"document_id": "doc-1", "chunk_count": 10}])
        return json_response({"detail": "não encontrado"}, 404)

    client = APIClient(transport=httpx.MockTransport(handler))

    assert client.health()["status"] == "ok"
    assert client.list_documents()[0]["document_id"] == "doc-1"


def test_timeout_has_clear_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = APIClient(transport=httpx.MockTransport(handler))

    with pytest.raises(APITimeoutError, match="demorou mais"):
        client.chat("Pergunta")


def test_unavailable_api_has_clear_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = APIClient(transport=httpx.MockTransport(handler))

    with pytest.raises(APIUnavailableError, match="indisponível"):
        client.health()


def test_chat_response_without_sources_is_preserved() -> None:
    payload = {
        "answer": "Não encontrei informações suficientes.",
        "sources": [],
        "retrieval_time_ms": 4,
        "generation_time_ms": 0,
    }
    client = APIClient(
        transport=httpx.MockTransport(lambda request: json_response(payload))
    )

    response = client.chat("Pergunta sem resposta", top_k=3)

    assert response["sources"] == []
    assert response["answer"].startswith("Não encontrei")


def test_chat_response_with_multiple_sources_is_preserved() -> None:
    payload = {
        "answer": "Resposta [Fonte 1] [Fonte 2].",
        "sources": [
            {"document_id": "a", "file_name": "a.pdf", "score": 0.8},
            {"document_id": "b", "file_name": "b.pdf", "score": 0.7},
        ],
        "retrieval_time_ms": 5,
        "generation_time_ms": 10,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/chat"
        assert body == {"question": "Tecnologia", "top_k": 5}
        return json_response(payload)

    client = APIClient(transport=httpx.MockTransport(handler))
    response = client.chat("Tecnologia")

    assert len(response["sources"]) == 2
    assert response["sources"][1]["file_name"] == "b.pdf"


def test_ingestion_sends_multipart_pdf() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/documents/ingest"
        assert request.method == "POST"
        assert "multipart/form-data" in request.headers["content-type"]
        assert b"%PDF-1.4" in request.content
        return json_response({"document_id": "doc-1", "chunk_count": 2}, 201)

    client = APIClient(transport=httpx.MockTransport(handler))

    response = client.ingest_document("teste.pdf", b"%PDF-1.4 fixture")

    assert response["document_id"] == "doc-1"


def test_ingestion_error_uses_api_detail() -> None:
    client = APIClient(
        transport=httpx.MockTransport(
            lambda request: json_response(
                {"detail": "O conteúdo enviado não possui assinatura PDF"},
                400,
            )
        )
    )

    with pytest.raises(APIResponseError, match="assinatura PDF") as error:
        client.ingest_document("invalido.pdf", b"invalido")

    assert error.value.status_code == 400


def test_delete_uses_document_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/documents/doc-1"
        return json_response({"document_id": "doc-1", "deleted_chunks": 12})

    client = APIClient(transport=httpx.MockTransport(handler))

    assert client.delete_document("doc-1")["deleted_chunks"] == 12
