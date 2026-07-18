"""CLI para ingestão de um PDF ou diretório."""

import argparse
import json
import logging
from pathlib import Path

from app.config import get_settings
from app.ingestion import IngestionService
from app.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingere PDFs acadêmicos com Docling")
    parser.add_argument("--input", type=Path, default=settings.documents_dir)
    parser.add_argument("--output", type=Path, default=settings.processed_dir)
    parser.add_argument("--chunk-size", type=int, default=settings.ingest_chunk_size)
    parser.add_argument("--overlap", type=int, default=settings.ingest_chunk_overlap)
    parser.add_argument("--device", default=settings.ingest_device)
    return parser


def main() -> int:
    settings = get_settings()
    args = build_parser().parse_args()
    configure_logging(settings.log_level, settings.logs_dir)
    try:
        report = IngestionService(
            output_dir=args.output,
            chunk_size=args.chunk_size,
            chunk_overlap=args.overlap,
            device=args.device,
            embedding_model=settings.embedding_model,
        ).ingest(args.input)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 2
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 1 if report.documents_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
