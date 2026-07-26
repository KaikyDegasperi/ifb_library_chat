from dataclasses import dataclass

import pytest
from streamlit.testing.v1 import AppTest

from frontend.api_client import APIResponseError, APITimeoutError
from frontend.pages.documents import _process_upload_batch, _validate_upload_batch


@dataclass
class FakeUpload:
    name: str
    content: bytes = b"%PDF-1.4 fixture"
    type: str | None = "application/pdf"

    @property
    def size(self) -> int:
        return len(self.content)

    def getvalue(self) -> bytes:
        return self.content


def test_selecting_a_pdf_enables_the_batch_button() -> None:
    app = AppTest.from_string(
        """
from frontend.pages.documents import _render_upload

class FakeClient:
    pass

_render_upload(FakeClient(), "admin-token")
"""
    ).run(timeout=10)

    assert app.button[0].disabled

    app.file_uploader[0].upload(
        "trabalho.pdf",
        b"%PDF-1.4 fixture",
        "application/pdf",
    ).run(timeout=10)

    assert not app.exception
    assert app.button[0].label == "Processar e indexar 1 PDF(s)"
    assert not app.button[0].disabled


def test_batch_validation_keeps_valid_files_and_reports_invalid_ones() -> None:
    valid = FakeUpload("valido.pdf")
    duplicate = FakeUpload("VALIDO.PDF")
    oversized = FakeUpload("grande.pdf", content=b"x" * 20)

    accepted, errors = _validate_upload_batch(
        [valid, duplicate, oversized],
        maximum_size_bytes=18,
    )

    assert accepted == [valid]
    assert any("nome repetido" in error for error in errors)
    assert any("excede o limite" in error for error in errors)


def test_batch_processing_continues_after_an_individual_failure() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.processed: list[str] = []

        def ingest_document(
            self,
            file_name: str,
            content: bytes,
            content_type: str,
            *,
            admin_token: str,
        ) -> dict[str, object]:
            self.processed.append(file_name)
            assert admin_token == "admin-token"
            if file_name == "falha.pdf":
                raise APITimeoutError("tempo limite")
            return {
                "file_name": file_name,
                "document_id": file_name,
                "chunk_count": 3,
            }

    client = FakeClient()
    progress: list[tuple[int, int, str]] = []
    uploads = [
        FakeUpload("primeiro.pdf"),
        FakeUpload("falha.pdf"),
        FakeUpload("ultimo.pdf"),
    ]

    results = _process_upload_batch(
        client,  # type: ignore[arg-type]
        uploads,
        admin_token="admin-token",
        on_progress=lambda current, total, name: progress.append(
            (current, total, name)
        ),
    )

    assert client.processed == [item.name for item in uploads]
    assert [result["status"] for result in results] == [
        "success",
        "error",
        "success",
    ]
    assert progress[-1] == (3, 3, "ultimo.pdf")


def test_batch_processing_propagates_admin_authentication_errors() -> None:
    class UnauthorizedClient:
        def ingest_document(self, *args: object, **kwargs: object) -> dict[str, object]:
            raise APIResponseError("acesso negado", 401)

    with pytest.raises(APIResponseError) as error:
        _process_upload_batch(
            UnauthorizedClient(),  # type: ignore[arg-type]
            [FakeUpload("teste.pdf")],
            admin_token="invalid-token",
        )

    assert error.value.status_code == 401
