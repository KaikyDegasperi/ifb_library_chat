"""Pipeline de ingestão de documentos acadêmicos com Docling."""

from app.ingestion.models import Chunk, IngestionReport
from app.ingestion.service import IngestionService

__all__ = ["Chunk", "IngestionReport", "IngestionService"]
