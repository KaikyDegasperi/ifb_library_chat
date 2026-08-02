"""Cliente HTTP único usado pela camada Streamlit."""

import os
from typing import Any

import httpx

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


class APIClientError(Exception):
    """Erro-base apresentável ao usuário."""


class APIUnavailableError(APIClientError):
    """A FastAPI não está acessível."""


class APITimeoutError(APIClientError):
    """A operação ultrapassou seu tempo limite."""


class APIResponseError(APIClientError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        default_timeout: float = 15.0,
        chat_timeout: float = 120.0,
        ingestion_timeout: float = 900.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL)
        ).rstrip("/")
        self.default_timeout = default_timeout
        self.chat_timeout = chat_timeout
        self.ingestion_timeout = ingestion_timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            transport=transport,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_documents(self) -> list[dict[str, Any]]:
        return self._request("GET", "/documents")

    def ingest_document(
        self,
        file_name: str,
        content: bytes,
        content_type: str = "application/pdf",
        *,
        admin_token: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/documents/ingest",
            timeout=self.ingestion_timeout,
            headers=self._admin_headers(admin_token),
            files={"file": (file_name, content, content_type)},
        )

    def delete_document(
        self,
        document_id: str,
        *,
        admin_token: str,
    ) -> dict[str, Any]:
        return self._request(
            "DELETE",
            f"/documents/{document_id}",
            headers=self._admin_headers(admin_token),
        )

    def chat(
        self,
        question: str,
        top_k: int | None = None,
        document_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"question": question}
        if top_k is not None:
            payload["top_k"] = top_k
        if document_id:
            payload["document_id"] = document_id
        if title:
            payload["title"] = title
        return self._request(
            "POST",
            "/chat",
            timeout=self.chat_timeout,
            json=payload,
        )

    def search(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"query": query}
        if top_k is not None:
            payload["top_k"] = top_k
        return self._request(
            "POST",
            "/search",
            json=payload,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                path,
                timeout=timeout or self.default_timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise APITimeoutError(
                "A operação demorou mais que o esperado. Tente novamente."
            ) from exc
        except httpx.ConnectError as exc:
            raise APIUnavailableError(
                "A API FastAPI está indisponível. Confirme se o backend está ativo."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise APIResponseError(
                self._error_detail(exc.response),
                exc.response.status_code,
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise APIClientError(
                "Não foi possível interpretar a resposta da API."
            ) from exc

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        if isinstance(detail, str) and detail:
            return detail
        if isinstance(detail, list):
            messages = [
                str(item.get("msg", "Entrada inválida"))
                for item in detail
                if isinstance(item, dict)
            ]
            if messages:
                return "; ".join(messages)
        return f"A API retornou o erro HTTP {response.status_code}."

    @staticmethod
    def _admin_headers(admin_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {admin_token}"}
