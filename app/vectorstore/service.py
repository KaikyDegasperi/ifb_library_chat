"""Persistência e consulta dos chunks no ChromaDB."""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import chromadb

from app.ingestion.models import Chunk
from app.vectorstore.embeddings import EmbeddingProvider
from app.vectorstore.models import IndexFileResult, IndexReport, SearchResult

logger = logging.getLogger(__name__)


class VectorIndexService:
    def __init__(
        self,
        persist_dir: Path | str,
        collection_name: str,
        embedding_provider: EmbeddingProvider,
        batch_size: int = 64,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_provider = embedding_provider
        self.batch_size = batch_size
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"embedding_model": embedding_provider.model_name},
            embedding_function=None,
        )
        stored_model = (self.collection.metadata or {}).get("embedding_model")
        if stored_model != embedding_provider.model_name:
            raise ValueError(
                "A collection foi criada com outro modelo de embeddings: "
                f"{stored_model!r}"
            )

    def index(self, input_path: Path | str) -> IndexReport:
        started = time.perf_counter()
        files = self._select_latest_versions(
            self._discover(Path(input_path).expanduser())
        )
        results: list[IndexFileResult] = []
        for path in files:
            try:
                result = self._index_file(path)
            except Exception as exc:
                logger.exception("Falha ao indexar %s", path)
                result = IndexFileResult(
                    file_path=str(path.resolve()),
                    document_id=None,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            results.append(result)

        return IndexReport(
            documents_indexed=sum(item.status == "indexed" for item in results),
            documents_skipped=sum(item.status == "skipped" for item in results),
            documents_failed=sum(item.status == "error" for item in results),
            chunks_indexed=sum(item.chunks for item in results if item.status == "indexed"),
            chunks_removed=sum(item.removed_chunks for item in results),
            elapsed_seconds=round(time.perf_counter() - started, 3),
            collection_count=self.collection.count(),
            results=results,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        title: str | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("A consulta não pode ser vazia")
        if top_k < 1:
            raise ValueError("top_k deve ser maior que zero")
        if self.collection.count() == 0:
            return []

        filters = []
        if document_id:
            filters.append({"document_id": document_id})
        if title:
            filters.append({"title": title})
        where: dict[str, Any] | None = None
        if len(filters) == 1:
            where = filters[0]
        elif filters:
            where = {"$and": filters}

        response = self.collection.query(
            query_embeddings=[self.embedding_provider.embed_query(query)],
            n_results=min(top_k, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = response["ids"][0]
        documents = (response["documents"] or [[]])[0]
        metadatas = (response["metadatas"] or [[]])[0]
        distances = (response["distances"] or [[]])[0]
        return [
            self._search_result(chunk_id, content, metadata, distance)
            for chunk_id, content, metadata, distance in zip(
                ids, documents, metadatas, distances, strict=True
            )
        ]

    def _index_file(self, path: Path) -> IndexFileResult:
        payload = json.loads(path.read_text(encoding="utf-8"))
        chunks = [Chunk.model_validate(item) for item in payload.get("chunks", [])]
        document_id = str(payload.get("document_id") or "")
        document_hash = str(payload.get("document_hash") or "")
        if not chunks or not document_id or not document_hash:
            raise ValueError("Arquivo de chunks vazio ou incompleto")
        if any(
            item.metadata.document_id != document_id
            or item.metadata.document_hash != document_hash
            for item in chunks
        ):
            raise ValueError("Metadados dos chunks divergem do cabeçalho do arquivo")

        ids = [self._chunk_id(item) for item in chunks]
        source_path = chunks[0].metadata.file_path
        existing = self.collection.get(
            where={"file_path": source_path},
            include=["metadatas"],
        )
        existing_ids = set(existing["ids"])
        existing_hashes = {
            str(metadata.get("document_hash"))
            for metadata in (existing["metadatas"] or [])
            if metadata
        }
        if existing_ids == set(ids) and existing_hashes == {document_hash}:
            return IndexFileResult(
                file_path=str(path.resolve()),
                document_id=document_id,
                status="skipped",
                chunks=len(chunks),
            )

        texts = [item.text for item in chunks]
        embeddings = self.embedding_provider.embed_documents(texts)
        if len(embeddings) != len(chunks):
            raise ValueError("O provedor retornou quantidade incorreta de embeddings")
        metadatas = [self._chroma_metadata(item) for item in chunks]
        for start in range(0, len(chunks), self.batch_size):
            end = start + self.batch_size
            self.collection.upsert(
                ids=ids[start:end],
                documents=texts[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )

        stale_ids = sorted(existing_ids - set(ids))
        if stale_ids:
            self.collection.delete(ids=stale_ids)
        logger.info("Documento indexado: %s (%d chunks)", source_path, len(chunks))
        return IndexFileResult(
            file_path=str(path.resolve()),
            document_id=document_id,
            status="indexed",
            chunks=len(chunks),
            removed_chunks=len(stale_ids),
        )

    @staticmethod
    def _discover(source: Path) -> list[Path]:
        if not source.exists():
            raise FileNotFoundError(f"Caminho de chunks inexistente: {source}")
        if source.is_file():
            if not source.name.endswith(".chunks.json"):
                raise ValueError("O arquivo deve terminar com .chunks.json")
            return [source]
        return sorted(source.glob("*.chunks.json"))

    @staticmethod
    def _select_latest_versions(files: list[Path]) -> list[Path]:
        latest: dict[str, tuple[str, Path]] = {}
        unreadable: list[Path] = []
        for path in files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                first = payload["chunks"][0]["metadata"]
                source_path = str(first["file_path"])
                processed_at = str(first["processed_at"])
            except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError):
                unreadable.append(path)
                continue
            current = latest.get(source_path)
            if current is None or processed_at > current[0]:
                latest[source_path] = (processed_at, path)
        return sorted(unreadable + [item[1] for item in latest.values()])

    @staticmethod
    def _chunk_id(chunk: Chunk) -> str:
        raw = (
            f"{chunk.metadata.document_hash}:"
            f"{chunk.metadata.chunk_index}:{chunk.text}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _chroma_metadata(chunk: Chunk) -> dict[str, str | int | float | bool | None]:
        data = chunk.metadata.model_dump(mode="json")
        return {key: value for key, value in data.items()}

    @staticmethod
    def _search_result(
        chunk_id: str,
        content: str | None,
        metadata: dict[str, Any] | None,
        distance: float | None,
    ) -> SearchResult:
        metadata = metadata or {}
        return SearchResult(
            chunk_id=chunk_id,
            content=content or "",
            similarity=round(1.0 - float(distance or 0.0), 6),
            document_id=str(metadata.get("document_id", "")),
            title=metadata.get("title") or None,
            file_name=str(metadata.get("file_name", "")),
            file_path=str(metadata.get("file_path", "")),
            page_start=metadata.get("page_start"),
            page_end=metadata.get("page_end"),
            section=metadata.get("section") or None,
            chunk_index=int(metadata.get("chunk_index", 0)),
            document_hash=str(metadata.get("document_hash", "")),
            processed_at=str(metadata.get("processed_at", "")),
        )
