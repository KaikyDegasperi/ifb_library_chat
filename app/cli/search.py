"""CLI para consultas de teste com o recuperador configurado."""

import argparse
import json
import time
from pathlib import Path

from app.config import get_settings
from app.logging_config import configure_logging
from app.retrieval import create_retriever


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Consulta o índice de recuperação")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=settings.search_top_k)
    parser.add_argument("--document-id")
    parser.add_argument("--title")
    parser.add_argument("--chroma-dir", type=Path, default=settings.chroma_dir)
    parser.add_argument("--collection", default=settings.chroma_collection)
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument(
        "--provider",
        choices=("bm25", "dense"),
        default=settings.retrieval_provider,
    )
    parser.add_argument("--processed-dir", type=Path, default=settings.processed_dir)
    return parser


def main() -> int:
    settings = get_settings()
    args = build_parser().parse_args()
    configure_logging(settings.log_level, settings.logs_dir)
    runtime_settings = settings.model_copy(
        update={
            "retrieval_provider": args.provider,
            "processed_dir": args.processed_dir,
            "chroma_dir": args.chroma_dir,
            "chroma_collection": args.collection,
            "embedding_model": args.model,
        }
    )
    service = create_retriever(runtime_settings)
    started = time.perf_counter()
    results = service.search(
        query=args.query,
        top_k=args.top_k,
        document_id=args.document_id,
        title=args.title,
    )
    print(
        json.dumps(
            {
                "query": args.query,
                "provider": args.provider,
                "elapsed_seconds": round(time.perf_counter() - started, 4),
                "results": [item.model_dump(mode="json") for item in results],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
