"""CLI para consultas semânticas de teste."""

import argparse
import json
import time
from pathlib import Path

from app.config import get_settings
from app.logging_config import configure_logging
from app.vectorstore import SentenceTransformerProvider, VectorIndexService


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Consulta o índice vetorial")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=settings.search_top_k)
    parser.add_argument("--document-id")
    parser.add_argument("--title")
    parser.add_argument("--chroma-dir", type=Path, default=settings.chroma_dir)
    parser.add_argument("--collection", default=settings.chroma_collection)
    parser.add_argument("--model", default=settings.embedding_model)
    return parser


def main() -> int:
    settings = get_settings()
    args = build_parser().parse_args()
    configure_logging(settings.log_level, settings.logs_dir)
    provider = SentenceTransformerProvider(args.model, settings.embedding_batch_size)
    service = VectorIndexService(
        persist_dir=args.chroma_dir,
        collection_name=args.collection,
        embedding_provider=provider,
    )
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
