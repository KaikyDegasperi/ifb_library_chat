"""Orquestra recuperação, contexto, geração e fontes."""

import logging
import re
import time
import unicodedata
from difflib import SequenceMatcher
from typing import Protocol

from app.observability import current_request_id
from app.rag.exceptions import InvalidQuestionError, LLMTimeoutError
from app.rag.llm import LanguageModelProvider
from app.rag.models import RAGObservation, RAGResponse, RAGSource, RAGTimings
from app.rag.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.vectorstore.models import SearchResult, SearchTimings

logger = logging.getLogger(__name__)

_QUERY_STOPWORDS = {
    "a",
    "algum",
    "alguma",
    "ao",
    "as",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "existe",
    "existem",
    "ha",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "qual",
    "quais",
    "que",
    "sobre",
    "tem",
    "temos",
    "tcc",
    "tccs",
    "trabalho",
    "trabalhos",
    "um",
    "uma",
}

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
        metrics_details_enabled: bool = False,
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
        self.metrics_details_enabled = metrics_details_enabled

    def answer(
        self,
        question: str,
        document_id: str | None = None,
        title: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        total_started = time.perf_counter()
        question = question.strip()
        if not question:
            raise InvalidQuestionError("A pergunta não pode ser vazia")
        if len(question) > self.max_question_chars:
            raise InvalidQuestionError(
                f"A pergunta excede {self.max_question_chars} caracteres"
            )
        effective_top_k = top_k or self.retrieval_top_k
        if effective_top_k < 1:
            raise InvalidQuestionError("top_k deve ser maior que zero")

        retrieval_started = time.perf_counter()
        search_timings = SearchTimings()
        try:
            timed_search = getattr(self.retriever, "search_with_timings", None)
            if callable(timed_search):
                retrieved, search_timings = timed_search(
                    question,
                    top_k=effective_top_k,
                    document_id=document_id,
                    title=title,
                )
            else:
                retrieved = self.retriever.search(
                    question,
                    top_k=effective_top_k,
                    document_id=document_id,
                    title=title,
                )
        except Exception as exc:
            error_type = type(exc).__name__
            logger.error("Falha ao recuperar contexto para o RAG: %s", error_type)
            return self._finish(
                answer=RETRIEVAL_FAILURE_ANSWER,
                sources=[],
                retrieval_time_ms=self._elapsed_ms(retrieval_started),
                generation_time_ms=0,
                total_started=total_started,
                search_timings=search_timings,
                context_preparation_time_ms=0,
                context_chars=0,
                status="retrieval_error",
                error_type=error_type,
            )
        retrieval_time = self._elapsed_ms(retrieval_started)

        context_started = time.perf_counter()
        selected = self._select_results(retrieved, question)
        context, selected = self._build_context(selected)
        if not selected:
            context_preparation_time = self._elapsed_ms(context_started)
            return self._finish(
                answer=NO_CONTEXT_ANSWER,
                sources=[],
                retrieval_time_ms=retrieval_time,
                generation_time_ms=0,
                total_started=total_started,
                search_timings=search_timings,
                context_preparation_time_ms=context_preparation_time,
                context_chars=0,
                status="no_context",
            )

        sources = [self._source(item) for item in selected]
        user_prompt = USER_PROMPT_TEMPLATE.format(
            question=question,
            context=context,
        )
        context_preparation_time = self._elapsed_ms(context_started)
        generation_started = time.perf_counter()
        error_type: str | None = None
        result_status = "ok"
        try:
            answer = self.llm_provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                timeout_seconds=self.llm_timeout_seconds,
            )
        except Exception as exc:
            error_type = type(exc).__name__
            result_status = (
                "llm_timeout" if isinstance(exc, LLMTimeoutError) else "llm_error"
            )
            logger.error("Falha controlada na geração do RAG: %s", error_type)
            answer = GENERATION_FAILURE_ANSWER
        generation_time = self._elapsed_ms(generation_started)
        return self._finish(
            answer=answer,
            sources=sources,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_started=total_started,
            search_timings=search_timings,
            context_preparation_time_ms=context_preparation_time,
            context_chars=len(context),
            status=result_status,
            error_type=error_type,
        )

    def _finish(
        self,
        *,
        answer: str,
        sources: list[RAGSource],
        retrieval_time_ms: int,
        generation_time_ms: int,
        total_started: float,
        search_timings: SearchTimings,
        context_preparation_time_ms: int,
        context_chars: int,
        status: str,
        error_type: str | None = None,
    ) -> RAGResponse:
        timings = RAGTimings(
            embedding_time_ms=search_timings.embedding_time_ms,
            vector_search_time_ms=search_timings.vector_search_time_ms,
            context_preparation_time_ms=context_preparation_time_ms,
            generation_time_ms=generation_time_ms,
            total_time_ms=self._elapsed_ms(total_started),
        )
        observation = RAGObservation(
            request_id=current_request_id(),
            status=status,
            source_count=len(sources),
            context_chars=context_chars,
            error_type=error_type,
            timings=timings,
        )
        log_fields: dict[str, object] = {
            "request_id": observation.request_id,
            "endpoint": "/chat",
            "status": status,
            "duration_ms": timings.total_time_ms,
            "source_count": observation.source_count,
            "context_chars": context_chars,
            "error_type": error_type or "none",
        }
        if self.metrics_details_enabled:
            log_fields.update(timings.model_dump(exclude={"total_time_ms"}))
        logger.info("rag_request_completed", extra=log_fields)
        return RAGResponse(
            answer=answer,
            sources=sources,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            observation=observation,
        )

    def _select_results(
        self,
        results: list[SearchResult],
        question: str,
    ) -> list[SearchResult]:
        selected: list[SearchResult] = []
        normalized: list[str] = []
        topic_terms = self._topic_terms(question)
        ranked = sorted(
            results,
            key=lambda item: (
                self._lexical_relevance(item, topic_terms),
                item.similarity,
            ),
            reverse=True,
        )
        for item in ranked:
            lexical_relevance = self._lexical_relevance(item, topic_terms)
            if (
                item.similarity < self.min_similarity
                and lexical_relevance < 0.5
            ) or not item.content.strip():
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

    @classmethod
    def _topic_terms(cls, question: str) -> set[str]:
        words = cls._normalize(question).split()
        return {
            cls._singularize(word)
            for word in words
            if len(word) >= 3 and word not in _QUERY_STOPWORDS
        }

    @classmethod
    def _lexical_relevance(
        cls,
        item: SearchResult,
        topic_terms: set[str],
    ) -> float:
        if not topic_terms:
            return 0.0
        searchable = " ".join(
            value
            for value in (item.title, item.section, item.content)
            if value
        )
        searchable_terms = {
            cls._singularize(word)
            for word in cls._normalize(searchable).split()
            if len(word) >= 3
        }
        return len(topic_terms & searchable_terms) / len(topic_terms)

    @staticmethod
    def _singularize(word: str) -> str:
        if len(word) > 4 and word.endswith("s"):
            return word[:-1]
        return word

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
