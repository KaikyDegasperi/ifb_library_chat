"""Catálogo de documentos derivado dos metadados do ChromaDB."""

from abc import ABC, abstractmethod
from typing import Any

from app.repositories.models import DocumentRecord


class DocumentRepository(ABC):
    @abstractmethod
    def list(self) -> list[DocumentRecord]: ...

    @abstractmethod
    def get(self, document_id: str) -> DocumentRecord | None: ...

    @abstractmethod
    def delete(self, document_id: str) -> int: ...


class ChromaDocumentRepository(DocumentRepository):
    def __init__(self, collection: Any) -> None:
        self.collection = collection

    def list(self) -> list[DocumentRecord]:
        response = self.collection.get(include=["metadatas"])
        grouped: dict[str, list[dict[str, Any]]] = {}
        for metadata in response["metadatas"] or []:
            if not metadata or not metadata.get("document_id"):
                continue
            grouped.setdefault(str(metadata["document_id"]), []).append(metadata)
        return sorted(
            (self._record(document_id, items) for document_id, items in grouped.items()),
            key=lambda item: (item.file_name.casefold(), item.document_id),
        )

    def get(self, document_id: str) -> DocumentRecord | None:
        response = self.collection.get(
            where={"document_id": document_id},
            include=["metadatas"],
        )
        metadatas = [item for item in response["metadatas"] or [] if item]
        if not metadatas:
            return None
        return self._record(document_id, metadatas)

    def delete(self, document_id: str) -> int:
        response = self.collection.get(
            where={"document_id": document_id},
            include=[],
        )
        ids = response["ids"]
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)

    @staticmethod
    def _record(
        document_id: str,
        metadatas: list[dict[str, Any]],
    ) -> DocumentRecord:
        first = metadatas[0]
        page_starts = [
            int(item["page_start"])
            for item in metadatas
            if item.get("page_start") is not None
        ]
        page_ends = [
            int(item["page_end"])
            for item in metadatas
            if item.get("page_end") is not None
        ]
        title = next((item.get("title") for item in metadatas if item.get("title")), None)
        author = next((item.get("author") for item in metadatas if item.get("author")), None)
        advisor = next((item.get("advisor") for item in metadatas if item.get("advisor")), None)
        coadvisor = next(
            (item.get("coadvisor") for item in metadatas if item.get("coadvisor")),
            None,
        )
        year = next((item.get("year") for item in metadatas if item.get("year")), None)
        return DocumentRecord(
            document_id=document_id,
            title=title,
            author=author,
            advisor=advisor,
            coadvisor=coadvisor,
            year=int(year) if year is not None else None,
            file_name=str(first.get("file_name", "")),
            file_path=str(first.get("file_path", "")),
            document_hash=str(first.get("document_hash", "")),
            processed_at=str(first.get("processed_at", "")),
            chunk_count=len(metadatas),
            page_start=min(page_starts) if page_starts else None,
            page_end=max(page_ends) if page_ends else None,
        )
