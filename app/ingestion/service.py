"""Serviço independente para converter PDFs e produzir chunks rastreáveis."""

import hashlib
import importlib.metadata
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docling.chunking import HybridChunker
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import HeadingHierarchyOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from app.ingestion.academic_metadata import (
    administrative_pages,
    extract_academic_metadata,
)
from app.ingestion.chunking import structured_pieces
from app.ingestion.models import (
    Chunk,
    ChunkMetadata,
    DocumentResult,
    IngestionReport,
)

logger = logging.getLogger(__name__)
PIPELINE_VERSION = 2
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class IngestionService:
    def __init__(
        self,
        output_dir: Path | str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        device: str = "auto",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        converter: Any | None = None,
        chunker: Any | None = None,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size")
        self.output_dir = Path(output_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        pipeline_options = PdfPipelineOptions(
            accelerator_options=AcceleratorOptions(device=device),
            heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),
            do_formula_enrichment=True,
            do_picture_classification=True,
        )
        self.converter = converter or DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            },
        )
        if chunker is not None:
            self.chunker = chunker
        else:
            tokenizer = HuggingFaceTokenizer(
                tokenizer=AutoTokenizer.from_pretrained(embedding_model),
                max_tokens=chunk_size,
            )
            self.chunker = HybridChunker(
                tokenizer=tokenizer,
                merge_peers=True,
                always_emit_headings=True,
            )

    def ingest(self, input_path: Path | str) -> IngestionReport:
        started = time.perf_counter()
        source = Path(input_path).expanduser()
        files = self._discover(source)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        manifest = self._load_manifest()
        results: list[DocumentResult] = []

        for pdf_path in files:
            try:
                result = self._ingest_file(pdf_path, manifest)
            except Exception as exc:
                logger.exception("Falha na ingestão de %s", pdf_path)
                result = DocumentResult(
                    document_id=None,
                    file_path=str(pdf_path.resolve()),
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            results.append(result)

        self._save_manifest(manifest)
        elapsed = time.perf_counter() - started
        report = IngestionReport(
            documents_processed=sum(item.status == "processed" for item in results),
            documents_skipped=sum(item.status == "skipped" for item in results),
            documents_failed=sum(item.status == "error" for item in results),
            chunks_created=sum(item.chunks for item in results if item.status == "processed"),
            elapsed_seconds=round(elapsed, 3),
            results=results,
        )
        self._save_report(report)
        return report

    def _discover(self, source: Path) -> list[Path]:
        if not source.exists():
            raise FileNotFoundError(f"Caminho de entrada inexistente: {source}")
        if source.is_file():
            if source.suffix.lower() != ".pdf":
                raise ValueError(f"O arquivo não é PDF: {source}")
            return [source]
        return sorted(
            path for path in source.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"
        )

    def _ingest_file(
        self,
        pdf_path: Path,
        manifest: dict[str, Any],
    ) -> DocumentResult:
        self._validate_pdf(pdf_path)
        document_hash = self._sha256(pdf_path)
        document_id = document_hash[:16]
        previous = manifest.get("documents", {}).get(document_hash)
        if (
            previous
            and previous.get("pipeline_version") == PIPELINE_VERSION
            and previous.get("ingestion_config") == self._ingestion_config()
            and Path(previous["output_file"]).exists()
            and Path(previous["structured_document_file"]).exists()
        ):
            logger.info("Documento sem alterações ignorado: %s", pdf_path)
            return DocumentResult(
                document_id=document_id,
                file_path=str(pdf_path.resolve()),
                status="skipped",
                chunks=previous.get("chunks", 0),
                document_hash=document_hash,
                output_file=previous["output_file"],
                structured_document_file=previous.get("structured_document_file"),
            )

        conversion = self.converter.convert(pdf_path, raises_on_error=True)
        document = conversion.document
        processed_at = datetime.now(UTC)
        academic = extract_academic_metadata(document, pdf_path.name)
        pieces = structured_pieces(
            document=document,
            chunker=self.chunker,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
            ignored_pages=administrative_pages(document),
        )
        chunks = [
            Chunk(
                text=piece.text,
                metadata=ChunkMetadata(
                    document_id=document_id,
                    title=academic.title,
                    author=academic.author,
                    advisor=academic.advisor,
                    coadvisor=academic.coadvisor,
                    year=academic.year,
                    file_name=pdf_path.name,
                    file_path=str(pdf_path.resolve()),
                    page_start=piece.page_start,
                    page_end=piece.page_end,
                    section=piece.section,
                    chunk_index=index,
                    document_hash=document_hash,
                    processed_at=processed_at,
                ),
            )
            for index, piece in enumerate(pieces)
        ]

        structured_path = self.output_dir / f"{document_id}.docling.json"
        chunks_path = self.output_dir / f"{document_id}.chunks.json"
        document.save_as_json(structured_path)
        self._write_json(
            chunks_path,
            {
                "document_id": document_id,
                "document_hash": document_hash,
                "pipeline_version": PIPELINE_VERSION,
                "ingestion_config": self._ingestion_config(),
                "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
            },
        )
        manifest.setdefault("documents", {})[document_hash] = {
            "document_id": document_id,
            "source_file": str(pdf_path.resolve()),
            "output_file": str(chunks_path.resolve()),
            "structured_document_file": str(structured_path.resolve()),
            "chunks": len(chunks),
            "processed_at": processed_at.isoformat(),
            "pipeline_version": PIPELINE_VERSION,
            "ingestion_config": self._ingestion_config(),
        }
        logger.info("Documento processado: %s (%d chunks)", pdf_path, len(chunks))
        return DocumentResult(
            document_id=document_id,
            file_path=str(pdf_path.resolve()),
            status="processed",
            chunks=len(chunks),
            document_hash=document_hash,
            output_file=str(chunks_path.resolve()),
            structured_document_file=str(structured_path.resolve()),
        )

    @staticmethod
    def _validate_pdf(path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"PDF inexistente: {path}")
        with path.open("rb") as file:
            if file.read(5) != b"%PDF-":
                raise ValueError("Arquivo não possui assinatura PDF válida")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @property
    def _manifest_path(self) -> Path:
        return self.output_dir / "manifest.json"

    def _load_manifest(self) -> dict[str, Any]:
        if not self._manifest_path.exists():
            return {"version": 1, "documents": {}}
        try:
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Manifesto inválido: {self._manifest_path}") from exc

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        self._write_json(self._manifest_path, manifest)

    def _save_report(self, report: IngestionReport) -> None:
        self._write_json(
            self.output_dir / "last-ingestion-report.json",
            report.model_dump(mode="json"),
        )

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    def _ingestion_config(self) -> dict[str, Any]:
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "tokenizer": self.embedding_model,
            "docling_version": importlib.metadata.version("docling"),
            "transformers_version": importlib.metadata.version("transformers"),
        }
