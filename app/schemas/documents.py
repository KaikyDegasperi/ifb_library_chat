from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "document_id": "d497a407dea443a3",
                "title": "Discalculia na realidade escolar",
                "author": "Adan Cardoso Franco Viana",
                "advisor": "Dra. Ana Maria Libório de Oliveira",
                "coadvisor": None,
                "year": 2022,
                "file_name": "Adan_Viana_CEST.pdf",
                "file_path": "/dados/Adan_Viana_CEST.pdf",
                "document_hash": "d497a407dea443a3...",
                "processed_at": "2026-07-11T20:29:43Z",
                "chunk_count": 184,
                "page_start": 1,
                "page_end": 15,
            }
        },
    )

    document_id: str
    title: str | None
    author: str | None
    advisor: str | None
    coadvisor: str | None
    year: int | None
    file_name: str
    file_path: str
    document_hash: str
    processed_at: str
    chunk_count: int
    page_start: int | None
    page_end: int | None


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted_chunks: int
