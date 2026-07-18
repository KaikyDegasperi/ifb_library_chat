"""CLI de diagnóstico ponta a ponta do acervo."""

import argparse
import json
from pathlib import Path
from typing import Any

import chromadb

from app.config import get_settings
from app.diagnostics import DiagnosticService, ReadableCollection
from app.vectorstore import SentenceTransformerProvider, VectorIndexService


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Verifica PDFs, artefatos Docling, chunks e ChromaDB"
    )
    parser.add_argument("--documents-dir", type=Path, default=settings.documents_dir)
    parser.add_argument("--processed-dir", type=Path, default=settings.processed_dir)
    parser.add_argument("--chroma-dir", type=Path, default=settings.chroma_dir)
    parser.add_argument("--collection", default=settings.chroma_collection)
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument("--probe-count", type=int, default=3)
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reindexa os chunks antes do diagnóstico; altera o ChromaDB",
    )
    return parser


def _open_collection(
    chroma_dir: Path,
    collection_name: str,
) -> tuple[ReadableCollection | None, str | None]:
    if not chroma_dir.is_dir():
        return None, "Diretório do ChromaDB inexistente"
    try:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        return client.get_collection(collection_name), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: coleção indisponível"


def _reindex(args: Any) -> ReadableCollection:
    provider = SentenceTransformerProvider(args.model, get_settings().embedding_batch_size)
    service = VectorIndexService(
        persist_dir=args.chroma_dir,
        collection_name=args.collection,
        embedding_provider=provider,
        batch_size=get_settings().embedding_batch_size,
    )
    report = service.index(args.processed_dir)
    if report.documents_failed:
        raise RuntimeError(
            f"Reindexação terminou com {report.documents_failed} falha(s)"
        )
    return service.collection


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.reindex:
            collection = _reindex(args)
            collection_error = None
        else:
            collection, collection_error = _open_collection(
                args.chroma_dir,
                args.collection,
            )
        report = DiagnosticService(
            documents_dir=args.documents_dir,
            processed_dir=args.processed_dir,
            chroma_dir=args.chroma_dir,
            chroma_collection=args.collection,
            embedding_model=args.model,
            collection=collection,
            collection_error=collection_error,
            technical_probe_count=args.probe_count,
            read_only=not args.reindex,
        ).run()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "error", "error_type": type(exc).__name__, "detail": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if report.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
