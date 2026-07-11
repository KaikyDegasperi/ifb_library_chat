"""Abstrações para modelos de embeddings."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identificador estável do modelo usado na collection."""

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Gera vetores para chunks."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Gera um vetor para consulta."""


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        self._model_name = model_name
        self.batch_size = batch_size
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model(self) -> Any:
        if self._model is None:
            from huggingface_hub.errors import LocalEntryNotFoundError
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    local_files_only=True,
                )
            except (OSError, LocalEntryNotFoundError):
                self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()
