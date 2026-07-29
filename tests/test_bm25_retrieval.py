import hashlib
import json
from pathlib import Path

from app.retrieval import BM25IndexService


def write_chunks(
    path: Path,
    *,
    document_id: str,
    file_name: str,
    title: str,
    texts: list[str],
) -> Path:
    document_hash = hashlib.sha256(document_id.encode()).hexdigest()
    path.write_text(
        json.dumps(
            {
                "document_id": document_id,
                "document_hash": document_hash,
                "chunks": [
                    {
                        "text": text,
                        "metadata": {
                            "document_id": document_id,
                            "title": title,
                            "file_name": file_name,
                            "file_path": f"/pdfs/{file_name}",
                            "page_start": index + 1,
                            "page_end": index + 1,
                            "section": "Teste",
                            "chunk_index": index,
                            "document_hash": document_hash,
                            "processed_at": "2026-01-01T00:00:00Z",
                        },
                    }
                    for index, text in enumerate(texts)
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_bm25_indexes_searches_and_filters_chunks(tmp_path: Path) -> None:
    write_chunks(
        tmp_path / "a.chunks.json",
        document_id="doc-a",
        file_name="geometria.pdf",
        title="Geometria",
        texts=["Geometria plana e triângulos"],
    )
    write_chunks(
        tmp_path / "b.chunks.json",
        document_id="doc-b",
        file_name="estatistica.pdf",
        title="Estatística",
        texts=["Estatística e análise de dados educacionais"],
    )
    service = BM25IndexService(tmp_path)

    report = service.index(tmp_path)
    results, timings = service.search_with_timings(
        "análise estatística dos dados",
        top_k=2,
    )
    filtered = service.search("dados", title="Estatística")

    assert report.documents_indexed == 2
    assert report.collection_count == 2
    assert results[0].document_id == "doc-b"
    assert results[0].similarity > 0
    assert timings.embedding_time_ms == 0
    assert timings.vector_search_time_ms >= 0
    assert {result.document_id for result in filtered} == {"doc-b"}


def test_bm25_update_replaces_document_and_delete_removes_it(tmp_path: Path) -> None:
    chunks_path = write_chunks(
        tmp_path / "a.chunks.json",
        document_id="doc-a",
        file_name="a.pdf",
        title="Documento A",
        texts=["conteúdo antigo", "outro trecho"],
    )
    service = BM25IndexService(tmp_path)
    service.index(chunks_path)
    write_chunks(
        chunks_path,
        document_id="doc-a",
        file_name="a.pdf",
        title="Documento A",
        texts=["conteúdo atualizado sobre discalculia"],
    )

    service.index(chunks_path)
    results = service.search("discalculia", top_k=5)
    removed = service.delete("doc-a")

    assert service.count == 0
    assert len(results) == 1
    assert "atualizado" in results[0].content
    assert removed == 1
    assert service.search("discalculia") == []


def test_bm25_startup_respects_active_document_ids(tmp_path: Path) -> None:
    write_chunks(
        tmp_path / "active.chunks.json",
        document_id="active",
        file_name="active.pdf",
        title="Ativo",
        texts=["matemática ativa"],
    )
    write_chunks(
        tmp_path / "deleted.chunks.json",
        document_id="deleted",
        file_name="deleted.pdf",
        title="Excluído",
        texts=["matemática excluída"],
    )
    service = BM25IndexService(tmp_path)

    service.index(tmp_path, allowed_document_ids={"active"})

    assert service.count == 1
    assert {result.document_id for result in service.search("matemática")} == {
        "active"
    }
