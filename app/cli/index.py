"""CLI de indexação dos chunks no ChromaDB."""

import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.logging_config import configure_logging
from app.vectorstore import SentenceTransformerProvider, VectorIndexService


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Indexa chunks no ChromaDB")
    parser.add_argument("--input", type=Path, default=settings.processed_dir)
    parser.add_argument("--chroma-dir", type=Path, default=settings.chroma_dir)
    parser.add_argument("--collection", default=settings.chroma_collection)
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument("--batch-size", type=int, default=settings.embedding_batch_size)
    return parser


def main() -> int:
    settings = get_settings()
    args = build_parser().parse_args()
    configure_logging(settings.log_level, settings.logs_dir)
    provider = SentenceTransformerProvider(args.model, args.batch_size)
    service = VectorIndexService(
        persist_dir=args.chroma_dir,
        collection_name=args.collection,
        embedding_provider=provider,
        batch_size=args.batch_size,
    )
    report = service.index(args.input)
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 1 if report.documents_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
