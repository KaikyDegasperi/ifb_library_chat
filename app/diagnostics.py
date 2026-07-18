"""Diagnóstico somente leitura dos artefatos do acervo e do ChromaDB."""

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.ingestion.models import Chunk


class ReadableCollection(Protocol):
    metadata: dict[str, Any] | None

    def count(self) -> int: ...

    def get(self, **kwargs: Any) -> dict[str, Any]: ...

    def query(self, **kwargs: Any) -> dict[str, Any]: ...


class DiagnosticIssue(BaseModel):
    code: str
    file_path: str | None = None
    document_id: str | None = None
    detail: str


class MissingMetadata(BaseModel):
    document_id: str
    file_name: str
    fields: list[str]


class DuplicateDocuments(BaseModel):
    document_hash: str
    files: list[str]


class DocumentStatus(BaseModel):
    document_id: str
    document_hash: str
    files: list[str]
    processed_by_docling: bool
    has_chunks: bool
    indexed_in_chromadb: bool
    chunk_count: int


class TechnicalProbe(BaseModel):
    probe_chunk_id: str
    returned_sources: int
    valid_sources: int
    status: str


class ChromaIntegrity(BaseModel):
    available: bool
    collection_count: int = 0
    indexed_documents: int = 0
    indexed_chunks: int = 0
    orphan_document_hashes: list[str] = Field(default_factory=list)
    missing_document_hashes: list[str] = Field(default_factory=list)
    empty_indexed_chunks: list[str] = Field(default_factory=list)
    source_errors: list[DiagnosticIssue] = Field(default_factory=list)
    technical_probes: list[TechnicalProbe] = Field(default_factory=list)
    collection_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class DiagnosticConfiguration(BaseModel):
    documents_dir: str
    processed_dir: str
    chroma_dir: str
    chroma_collection: str
    embedding_model: str
    technical_probe_count: int
    read_only: bool


class DiagnosticReport(BaseModel):
    status: str
    total_pdfs: int
    unique_pdf_hashes: int
    total_processed: int
    total_with_chunks: int
    total_indexed: int
    total_chunks: int
    average_chunks_per_document: float
    median_chunks_per_document: float
    documents: list[DocumentStatus]
    documents_with_errors: list[DiagnosticIssue]
    missing_metadata: list[MissingMetadata]
    duplicates: list[DuplicateDocuments]
    empty_chunks: list[DiagnosticIssue]
    documents_without_indexed_pages: list[str]
    chromadb_integrity: ChromaIntegrity
    configuration: DiagnosticConfiguration


class DiagnosticService:
    REQUIRED_METADATA = ("title", "author", "year", "advisor")

    def __init__(
        self,
        *,
        documents_dir: Path | str,
        processed_dir: Path | str,
        chroma_dir: Path | str,
        chroma_collection: str,
        embedding_model: str,
        collection: ReadableCollection | None,
        collection_error: str | None = None,
        technical_probe_count: int = 3,
        read_only: bool = True,
    ) -> None:
        if technical_probe_count < 0:
            raise ValueError("technical_probe_count não pode ser negativo")
        self.documents_dir = Path(documents_dir).expanduser().resolve()
        self.processed_dir = Path(processed_dir).expanduser().resolve()
        self.chroma_dir = Path(chroma_dir).expanduser().resolve()
        self.chroma_collection = chroma_collection
        self.embedding_model = embedding_model
        self.collection = collection
        self.collection_error = collection_error
        self.technical_probe_count = technical_probe_count
        self.read_only = read_only

    def run(self) -> DiagnosticReport:
        if not self.documents_dir.is_dir():
            raise FileNotFoundError(
                f"Diretório de PDFs inexistente: {self.documents_dir}"
            )

        pdfs = sorted(
            path
            for path in self.documents_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        )
        errors: list[DiagnosticIssue] = []
        hashes: dict[str, list[Path]] = {}
        for pdf in pdfs:
            try:
                hashes.setdefault(self._sha256(pdf), []).append(pdf)
            except OSError as exc:
                errors.append(
                    DiagnosticIssue(
                        code="pdf_read_error",
                        file_path=str(pdf),
                        detail=type(exc).__name__,
                    )
                )

        if not pdfs:
            errors.append(
                DiagnosticIssue(
                    code="no_pdfs_found",
                    file_path=str(self.documents_dir),
                    detail="Nenhum PDF encontrado no diretório configurado",
                )
            )

        processed_hashes: set[str] = set()
        chunked_hashes: set[str] = set()
        chunk_counts: dict[str, int] = {item: 0 for item in hashes}
        page_numbers: dict[str, set[int]] = {}
        missing_metadata: list[MissingMetadata] = []
        empty_chunks: list[DiagnosticIssue] = []

        for document_hash, paths in hashes.items():
            document_id = document_hash[:16]
            docling_path = self.processed_dir / f"{document_id}.docling.json"
            chunks_path = self.processed_dir / f"{document_id}.chunks.json"
            pages = self._read_docling_pages(docling_path, document_id, errors)
            if pages is not None:
                processed_hashes.add(document_hash)
                page_numbers[document_hash] = pages
            chunks = self._read_chunks(
                chunks_path,
                document_hash,
                document_id,
                errors,
            )
            if chunks is None:
                continue
            chunked_hashes.add(document_hash)
            chunk_counts[document_hash] = len(chunks)
            self._inspect_chunks(chunks, chunks_path, empty_chunks)
            fields = [
                field
                for field in self.REQUIRED_METADATA
                if not any(
                    self._metadata_present(getattr(chunk.metadata, field))
                    for chunk in chunks
                )
            ]
            if fields:
                missing_metadata.append(
                    MissingMetadata(
                        document_id=document_id,
                        file_name=paths[0].name,
                        fields=fields,
                    )
                )

        integrity, indexed_hashes, documents_without_pages = self._inspect_chroma(
            set(hashes),
            page_numbers,
        )
        counts = list(chunk_counts.values())
        duplicates = [
            DuplicateDocuments(
                document_hash=document_hash,
                files=[str(path) for path in paths],
            )
            for document_hash, paths in hashes.items()
            if len(paths) > 1
        ]
        has_integrity_issue = (
            not integrity.available
            or bool(integrity.orphan_document_hashes)
            or bool(integrity.missing_document_hashes)
            or bool(integrity.empty_indexed_chunks)
            or bool(integrity.source_errors)
            or any(probe.status != "ok" for probe in integrity.technical_probes)
        )
        status = (
            "issues"
            if errors
            or missing_metadata
            or duplicates
            or empty_chunks
            or documents_without_pages
            or has_integrity_issue
            else "ok"
        )
        documents = [
            DocumentStatus(
                document_id=document_hash[:16],
                document_hash=document_hash,
                files=[str(path) for path in paths],
                processed_by_docling=document_hash in processed_hashes,
                has_chunks=document_hash in chunked_hashes,
                indexed_in_chromadb=document_hash in indexed_hashes,
                chunk_count=chunk_counts[document_hash],
            )
            for document_hash, paths in hashes.items()
        ]
        return DiagnosticReport(
            status=status,
            total_pdfs=len(pdfs),
            unique_pdf_hashes=len(hashes),
            total_processed=len(processed_hashes),
            total_with_chunks=len(chunked_hashes),
            total_indexed=len(set(hashes) & indexed_hashes),
            total_chunks=sum(chunk_counts.values()),
            average_chunks_per_document=(
                round(statistics.mean(counts), 2) if counts else 0.0
            ),
            median_chunks_per_document=(
                float(statistics.median(counts)) if counts else 0.0
            ),
            documents=documents,
            documents_with_errors=errors,
            missing_metadata=sorted(
                missing_metadata,
                key=lambda item: (item.file_name.casefold(), item.document_id),
            ),
            duplicates=duplicates,
            empty_chunks=empty_chunks,
            documents_without_indexed_pages=sorted(documents_without_pages),
            chromadb_integrity=integrity,
            configuration=DiagnosticConfiguration(
                documents_dir=str(self.documents_dir),
                processed_dir=str(self.processed_dir),
                chroma_dir=str(self.chroma_dir),
                chroma_collection=self.chroma_collection,
                embedding_model=self.embedding_model,
                technical_probe_count=self.technical_probe_count,
                read_only=self.read_only,
            ),
        )

    def _read_docling_pages(
        self,
        path: Path,
        document_id: str,
        errors: list[DiagnosticIssue],
    ) -> set[int] | None:
        if not path.is_file():
            errors.append(
                DiagnosticIssue(
                    code="missing_docling_artifact",
                    file_path=str(path),
                    document_id=document_id,
                    detail="Artefato estruturado do Docling ausente",
                )
            )
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            pages = payload.get("pages", {})
            if not isinstance(pages, (dict, list)):
                raise ValueError("campo pages inválido")
            if isinstance(pages, dict):
                page_numbers = {int(page) for page in pages}
            else:
                page_numbers = set(range(1, len(pages) + 1))
            if not page_numbers:
                errors.append(
                    DiagnosticIssue(
                        code="docling_without_pages",
                        file_path=str(path),
                        document_id=document_id,
                        detail="Artefato Docling sem páginas",
                    )
                )
            return page_numbers
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            errors.append(
                DiagnosticIssue(
                    code="invalid_docling_artifact",
                    file_path=str(path),
                    document_id=document_id,
                    detail=type(exc).__name__,
                )
            )
            return None

    def _read_chunks(
        self,
        path: Path,
        expected_hash: str,
        document_id: str,
        errors: list[DiagnosticIssue],
    ) -> list[Chunk] | None:
        if not path.is_file():
            errors.append(
                DiagnosticIssue(
                    code="missing_chunks_artifact",
                    file_path=str(path),
                    document_id=document_id,
                    detail="Artefato de chunks ausente",
                )
            )
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("document_hash") != expected_hash:
                raise ValueError("document_hash divergente")
            chunks = [Chunk.model_validate(item) for item in payload.get("chunks", [])]
            if any(
                chunk.metadata.document_hash != expected_hash
                or chunk.metadata.document_id != document_id
                for chunk in chunks
            ):
                raise ValueError("metadados dos chunks divergentes")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            errors.append(
                DiagnosticIssue(
                    code="invalid_chunks_artifact",
                    file_path=str(path),
                    document_id=document_id,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
            return None
        if not chunks:
            errors.append(
                DiagnosticIssue(
                    code="document_without_chunks",
                    file_path=str(path),
                    document_id=document_id,
                    detail="O artefato não possui chunks",
                )
            )
        return chunks

    @staticmethod
    def _inspect_chunks(
        chunks: list[Chunk],
        path: Path,
        empty_chunks: list[DiagnosticIssue],
    ) -> None:
        for chunk in chunks:
            if not chunk.text.strip():
                empty_chunks.append(
                    DiagnosticIssue(
                        code="empty_chunk",
                        file_path=str(path),
                        document_id=chunk.metadata.document_id,
                        detail=f"chunk_index={chunk.metadata.chunk_index}",
                    )
                )

    @staticmethod
    def _metadata_present(value: object) -> bool:
        if isinstance(value, str):
            return bool(value.strip())
        return value is not None

    def _inspect_chroma(
        self,
        pdf_hashes: set[str],
        page_numbers: dict[str, set[int]],
    ) -> tuple[ChromaIntegrity, set[str], set[str]]:
        if self.collection is None:
            return (
                ChromaIntegrity(available=False, error=self.collection_error),
                set(),
                set(),
            )
        try:
            response = self.collection.get(include=["documents", "metadatas"])
            ids = list(response.get("ids") or [])
            documents = list(response.get("documents") or [])
            metadatas = list(response.get("metadatas") or [])
            indexed_hashes = {
                str(metadata.get("document_hash"))
                for metadata in metadatas
                if metadata and metadata.get("document_hash")
            }
            grouped_pages: dict[str, list[int]] = {}
            empty_indexed_chunks: list[str] = []
            for index, chunk_id in enumerate(ids):
                document = documents[index] if index < len(documents) else None
                metadata = metadatas[index] if index < len(metadatas) else None
                if not str(document or "").strip():
                    empty_indexed_chunks.append(str(chunk_id))
                if metadata and metadata.get("document_hash"):
                    document_hash = str(metadata["document_hash"])
                    if metadata.get("page_start") is not None:
                        grouped_pages.setdefault(document_hash, []).append(
                            int(metadata["page_start"])
                        )
                    else:
                        grouped_pages.setdefault(document_hash, [])
            documents_without_pages = {
                document_hash
                for document_hash in indexed_hashes
                if not grouped_pages.get(document_hash)
            }
            source_errors, probes = self._run_technical_probes(page_numbers)
            integrity = ChromaIntegrity(
                available=True,
                collection_count=self.collection.count(),
                indexed_documents=len(indexed_hashes),
                indexed_chunks=len(ids),
                orphan_document_hashes=sorted(indexed_hashes - pdf_hashes),
                missing_document_hashes=sorted(pdf_hashes - indexed_hashes),
                empty_indexed_chunks=empty_indexed_chunks,
                source_errors=source_errors,
                technical_probes=probes,
                collection_metadata=dict(self.collection.metadata or {}),
            )
            return integrity, indexed_hashes, documents_without_pages
        except Exception as exc:
            return (
                ChromaIntegrity(
                    available=False,
                    error=f"{type(exc).__name__}: {exc}",
                ),
                set(),
                set(),
            )

    def _run_technical_probes(
        self,
        page_numbers: dict[str, set[int]],
    ) -> tuple[list[DiagnosticIssue], list[TechnicalProbe]]:
        if self.technical_probe_count == 0 or self.collection is None:
            return [], []
        sample = self.collection.get(
            limit=self.technical_probe_count,
            include=["embeddings", "metadatas"],
        )
        ids = list(sample.get("ids") or [])
        raw_embeddings = sample.get("embeddings")
        embeddings = [] if raw_embeddings is None else list(raw_embeddings)
        errors: list[DiagnosticIssue] = []
        probes: list[TechnicalProbe] = []
        result_count = max(1, min(3, self.collection.count()))
        for index, chunk_id in enumerate(ids):
            if index >= len(embeddings):
                errors.append(
                    DiagnosticIssue(
                        code="missing_probe_embedding",
                        detail=f"Chunk sem embedding: {chunk_id}",
                    )
                )
                continue
            response = self.collection.query(
                query_embeddings=[embeddings[index]],
                n_results=result_count,
                include=["metadatas", "distances"],
            )
            returned_ids = list((response.get("ids") or [[]])[0])
            returned_metadata = list((response.get("metadatas") or [[]])[0])
            valid = 0
            for result_index, result_id in enumerate(returned_ids):
                metadata = (
                    returned_metadata[result_index]
                    if result_index < len(returned_metadata)
                    else None
                )
                issue = self._validate_source(str(result_id), metadata, page_numbers)
                if issue is None:
                    valid += 1
                else:
                    errors.append(issue)
            original_returned = str(chunk_id) in {str(item) for item in returned_ids}
            probes.append(
                TechnicalProbe(
                    probe_chunk_id=str(chunk_id),
                    returned_sources=len(returned_ids),
                    valid_sources=valid,
                    status=(
                        "ok"
                        if returned_ids
                        and valid == len(returned_ids)
                        and original_returned
                        else "error"
                    ),
                )
            )
        return errors, probes

    def _validate_source(
        self,
        chunk_id: str,
        metadata: dict[str, Any] | None,
        page_numbers: dict[str, set[int]],
    ) -> DiagnosticIssue | None:
        if not metadata:
            return DiagnosticIssue(
                code="source_without_metadata",
                detail=f"Fonte {chunk_id} sem metadados",
            )
        raw_path = str(metadata.get("file_path") or "")
        source = Path(raw_path).expanduser() if raw_path else Path()
        if not source.is_file():
            source = self.documents_dir / str(metadata.get("file_name") or "")
        if not source.is_file():
            return DiagnosticIssue(
                code="source_file_missing",
                file_path=raw_path or None,
                document_id=str(metadata.get("document_id") or "") or None,
                detail=f"Arquivo da fonte {chunk_id} não existe",
            )
        document_hash = str(metadata.get("document_hash") or "")
        try:
            page_start = int(metadata["page_start"])
            page_end = int(metadata.get("page_end") or page_start)
        except (KeyError, TypeError, ValueError):
            return DiagnosticIssue(
                code="source_page_missing",
                file_path=str(source),
                document_id=str(metadata.get("document_id") or "") or None,
                detail=f"Fonte {chunk_id} sem página válida",
            )
        available_pages = page_numbers.get(document_hash, set())
        if (
            page_start < 1
            or page_end < page_start
            or page_start not in available_pages
            or page_end not in available_pages
        ):
            return DiagnosticIssue(
                code="source_page_out_of_range",
                file_path=str(source),
                document_id=str(metadata.get("document_id") or "") or None,
                detail=f"Fonte {chunk_id} aponta para páginas {page_start}-{page_end}",
            )
        return None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
