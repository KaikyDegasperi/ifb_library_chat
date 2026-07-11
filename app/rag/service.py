"""Orquestra recuperação, contexto, geração e fontes."""

import logging
import re
import time
import unicodedata
from difflib import SequenceMatcher
from typing import Protocol

from app.rag.exceptions import InvalidQuestionError
from app.rag.llm import LanguageModelProvider
from app.rag.models import RAGResponse, RAGSource
from app.rag.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.vectorstore.models import SearchResult

logger = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = (
    "Não encontrei informações suficientemente relevantes nos TCCs indexados "
    "para responder a essa pergunta."
)
RETRIEVAL_FAILURE_ANSWER = (
    "Não foi possível consultar o acervo neste momento. Tente novamente mais tarde."
)
GENERATION_FAILURE_ANSWER = (
    "Encontrei trechos relacionados, mas não foi possível gerar a resposta neste "
    "momento. Consulte as fontes apresentadas abaixo."
)


class Retriever(Protocol):
    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        title: str | None = None,
    ) -> list[SearchResult]: ...


class RAGService:
    def __init__(
        self,
        retriever: Retriever,
        llm_provider: LanguageModelProvider,
        retrieval_top_k: int = 8,
        min_similarity: float = 0.35,
        max_context_chars: int = 12_000,
        max_question_chars: int = 2_000,
        duplicate_threshold: float = 0.92,
        llm_timeout_seconds: float = 30.0,
    ) -> None:
        if retrieval_top_k < 1 or max_context_chars < 1 or max_question_chars < 1:
            raise ValueError("Limites do RAG devem ser maiores que zero")
        if not -1.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity deve estar entre -1 e 1")
        if not 0.0 <= duplicate_threshold <= 1.0:
            raise ValueError("duplicate_threshold deve estar entre 0 e 1")
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.retrieval_top_k = retrieval_top_k
        self.min_similarity = min_similarity
        self.max_context_chars = max_context_chars
        self.max_question_chars = max_question_chars
        self.duplicate_threshold = duplicate_threshold
        self.llm_timeout_seconds = llm_timeout_seconds

    def answer(
        self,
        question: str,
        document_id: str | None = None,
        title: str | None = None,
    ) -> RAGResponse:
        question = question.strip()
        if not question:
            raise InvalidQuestionError("A pergunta não pode ser vazia")
        if len(question) > self.max_question_chars:
            raise InvalidQuestionError(
                f"A pergunta excede {self.max_question_chars} caracteres"
            )

        retrieval_started = time.perf_counter()
        try:
            retrieved = self.retriever.search(
                question,
                top_k=self.retrieval_top_k,
                document_id=document_id,
                title=title,
            )
        except Exception:
            logger.exception("Falha ao recuperar contexto para o RAG")
            return RAGResponse(
                answer=RETRIEVAL_FAILURE_ANSWER,
                sources=[],
                retrieval_time_ms=self._elapsed_ms(retrieval_started),
                generation_time_ms=0,
            )
        retrieval_time = self._elapsed_ms(retrieval_started)
        selected = self._select_results(retrieved)
        context, selected = self._build_context(selected)
        if not selected:
            return RAGResponse(
                answer=NO_CONTEXT_ANSWER,
                sources=[],
                retrieval_time_ms=retrieval_time,
                generation_time_ms=0,
            )

        sources = [self._source(item) for item in selected]
        user_prompt = USER_PROMPT_TEMPLATE.format(
            question=question,
            context=context,
        )
        generation_started = time.perf_counter()
        try:
            answer = self.llm_provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                timeout_seconds=self.llm_timeout_seconds,
            )
        except Exception:
            logger.exception("Falha controlada na geração do RAG")
            answer = GENERATION_FAILURE_ANSWER
        return RAGResponse(
            answer=answer,
            sources=sources,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=self._elapsed_ms(generation_started),
        )

    def _select_results(self, results: list[SearchResult]) -> list[SearchResult]:
        selected: list[SearchResult] = []
        normalized: list[str] = []
        for item in results:
            if item.similarity < self.min_similarity or not item.content.strip():
                continue
            candidate = self._normalize(item.content)
            if not candidate:
                continue
            if any(
                SequenceMatcher(None, candidate, previous).ratio()
                >= self.duplicate_threshold
                for previous in normalized
            ):
                continue
            selected.append(item)
            normalized.append(candidate)
        return selected

    def _build_context(
        self,
        results: list[SearchResult],
    ) -> tuple[str, list[SearchResult]]:
        blocks: list[str] = []
        included: list[SearchResult] = []
        used = 0
        for item in results:
            source_number = len(included) + 1
            page = self._page_label(item.page_start, item.page_end)
            header = (
                f"[Fonte {source_number}]\n"
                f"Arquivo: {item.file_name}\n"
                f"Título: {item.title or ''}\n"
                f"Página(s): {page}\n"
                f"Seção: {item.section or ''}\n"
                "Trecho:\n"
            )
            separator_size = 2 if blocks else 0
            available = self.max_context_chars - used - len(header) - separator_size
            if available <= 0:
                break
            content = item.content.strip()[:available]
            if not content:
                break
            block = f"{header}{content}"
            blocks.append(block)
            included.append(item)
            used += len(block) + separator_size
            if len(content) < len(item.content.strip()):
                break
        return "\n\n".join(blocks), included

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", normalized).strip()

    @staticmethod
    def _source(item: SearchResult) -> RAGSource:
        return RAGSource(
            document_id=item.document_id,
            title=item.title,
            file_name=item.file_name,
            page_start=item.page_start,
            page_end=item.page_end,
            section=item.section,
            chunk_id=item.chunk_id,
            score=item.similarity,
        )

    @staticmethod
    def _page_label(start: int | None, end: int | None) -> str:
        if start is None:
            return ""
        if end is None or end == start:
            return str(start)
        return f"{start}-{end}"

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((time.perf_counter() - started) * 1000))
