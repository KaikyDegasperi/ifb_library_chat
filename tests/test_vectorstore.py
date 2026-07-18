import hashlib
import json
import math
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from app.vectorstore.embeddings import EmbeddingProvider
from app.vectorstore.service import VectorIndexService


class FakeEmbeddingProvider(EmbeddingProvider):
    @property
    def model_name(self) -> str:
        return "fake-portuguese-v1"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        lowered = text.lower()
        vector = [
            float(lowered.count("matemática")),
            float(lowered.count("inclusão")),
            float(lowered.count("geometria")),
            0.1,
        ]
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector]


def write_chunks(
    path: Path,
    source_pdf: Path,
    document_hash: str,
    texts: list[str],
    title: str | None = "TCC sobre Matemática",
    processed_at: str | None = None,
) -> Path:
    document_id = document_hash[:16]
    chunks = []
    for index, text in enumerate(texts):
        chunks.append(
            {
                "text": text,
                "metadata": {
                    "document_id": document_id,
                    "title": title,
                    "file_name": source_pdf.name,
                    "file_path": str(source_pdf.resolve()),
                    "page_start": index + 1,
                    "page_end": index + 1,
                    "section": "Seção de teste" if index else None,
                    "chunk_index": index,
                    "document_hash": document_hash,
                    "processed_at": processed_at or datetime.now(UTC).isoformat(),
                },
            }
        )
    path.write_text(
        json.dumps(
            {
                "document_id": document_id,
                "document_hash": document_hash,
                "chunks": chunks,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def make_service(tmp_path: Path) -> VectorIndexService:
    return VectorIndexService(
        persist_dir=tmp_path / "chroma",
        collection_name="tccs_test",
        embedding_provider=FakeEmbeddingProvider(),
    )


def test_chunks_are_persisted_without_duplicates(tmp_path: Path) -> None:
    source = tmp_path / "tcc.pdf"
    chunks_file = write_chunks(
        tmp_path / "tcc.chunks.json",
        source,
        hashlib.sha256(b"versao-1").hexdigest(),
        ["Ensino de matemática", "Geometria plana"],
    )
    service = make_service(tmp_path)

    first = service.index(chunks_file)
    second = service.index(chunks_file)
    restarted = make_service(tmp_path)

    assert first.documents_indexed == 1
    assert first.collection_count == 2
    assert second.documents_skipped == 1
    assert second.collection_count == 2
    assert restarted.collection.count() == 2


def test_updated_pdf_replaces_old_chunks(tmp_path: Path) -> None:
    source = tmp_path / "mesmo-tcc.pdf"
    chunks_file = tmp_path / "mesmo-tcc.chunks.json"
    old_hash = hashlib.sha256(b"antigo").hexdigest()
    new_hash = hashlib.sha256(b"novo").hexdigest()
    service = make_service(tmp_path)
    service.index(
        write_chunks(
            chunks_file,
            source,
            old_hash,
            ["Matemática antiga", "Outro trecho antigo"],
        )
    )

    report = service.index(
        write_chunks(chunks_file, source, new_hash, ["Matemática atualizada"])
    )
    stored = service.collection.get(include=["metadatas"])

    assert report.documents_indexed == 1
    assert report.chunks_removed == 2
    assert report.collection_count == 1
    assert {item["document_hash"] for item in stored["metadatas"] or []} == {
        new_hash
    }


def test_semantic_search_returns_sources_and_similarity(tmp_path: Path) -> None:
    source = tmp_path / "fontes.pdf"
    document_hash = hashlib.sha256(b"busca").hexdigest()
    service = make_service(tmp_path)
    service.index(
        write_chunks(
            tmp_path / "fontes.chunks.json",
            source,
            document_hash,
            [
                "Práticas de inclusão na escola",
                "Conceitos de geometria no ensino de matemática",
            ],
            title=None,
        )
    )

    results = service.search("inclusão", top_k=1)

    assert len(results) == 1
    assert "inclusão" in results[0].content
    assert results[0].file_name == "fontes.pdf"
    assert results[0].page_start == 1
    assert results[0].similarity > 0.9


def test_search_measures_embedding_and_chroma_separately(tmp_path: Path) -> None:
    source = tmp_path / "metricas.pdf"
    service = make_service(tmp_path)
    service.index(
        write_chunks(
            tmp_path / "metricas.chunks.json",
            source,
            hashlib.sha256(b"metricas").hexdigest(),
            ["Matemática inclusiva"],
        )
    )
    original_embed = service.embedding_provider.embed_query
    original_collection = service.collection

    def delayed_embed(text: str) -> list[float]:
        time.sleep(0.003)
        return original_embed(text)

    class DelayedCollection:
        def __getattr__(self, name: str):
            return getattr(original_collection, name)

        def query(self, **kwargs):
            time.sleep(0.003)
            return original_collection.query(**kwargs)

    service.embedding_provider.embed_query = delayed_embed
    service.collection = DelayedCollection()

    results, timings = service.search_with_timings("inclusão", top_k=1)

    assert len(results) == 1
    assert timings.embedding_time_ms >= 2
    assert timings.vector_search_time_ms >= 2


def test_search_filters_by_document_and_title(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    first_hash = hashlib.sha256(b"primeiro").hexdigest()
    second_hash = hashlib.sha256(b"segundo").hexdigest()
    service.index(
        write_chunks(
            tmp_path / "a.chunks.json",
            tmp_path / "a.pdf",
            first_hash,
            ["Matemática e geometria"],
            title="Primeiro TCC",
        )
    )
    service.index(
        write_chunks(
            tmp_path / "b.chunks.json",
            tmp_path / "b.pdf",
            second_hash,
            ["Matemática inclusiva"],
            title="Segundo TCC",
        )
    )

    by_document = service.search(
        "matemática",
        document_id=first_hash[:16],
    )
    by_title = service.search("matemática", title="Segundo TCC")

    assert {result.document_id for result in by_document} == {first_hash[:16]}
    assert {result.title for result in by_title} == {"Segundo TCC"}


def test_directory_indexes_only_latest_version_per_source(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    source = tmp_path / "versionado.pdf"
    old_hash = hashlib.sha256(b"versao-antiga").hexdigest()
    new_hash = hashlib.sha256(b"versao-nova").hexdigest()
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    write_chunks(
        chunks_dir / "old.chunks.json",
        source,
        old_hash,
        ["Conteúdo antigo"],
        processed_at="2025-01-01T00:00:00+00:00",
    )
    write_chunks(
        chunks_dir / "new.chunks.json",
        source,
        new_hash,
        ["Conteúdo novo sobre matemática"],
        processed_at="2026-01-01T00:00:00+00:00",
    )

    report = service.index(chunks_dir)
    stored = service.collection.get(include=["metadatas"])

    assert report.documents_indexed == 1
    assert report.collection_count == 1
    assert (stored["metadatas"] or [])[0]["document_hash"] == new_hash
