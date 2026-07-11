from dataclasses import dataclass, field

import pytest

from app.rag.exceptions import InvalidQuestionError, LLMTimeoutError
from app.rag.llm import LanguageModelProvider
from app.rag.service import (
    GENERATION_FAILURE_ANSWER,
    NO_CONTEXT_ANSWER,
    RETRIEVAL_FAILURE_ANSWER,
    RAGService,
)
from app.vectorstore.models import SearchResult


def result(
    content: str,
    similarity: float = 0.8,
    chunk_id: str = "chunk-1",
    page: int = 3,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        content=content,
        similarity=similarity,
        document_id="documento-1",
        title="Ensino de Matemática",
        file_name="tcc.pdf",
        file_path="/documentos/tcc.pdf",
        page_start=page,
        page_end=page,
        section="Introdução",
        chunk_index=page,
        document_hash="hash-1",
        processed_at="2026-01-01T00:00:00Z",
    )


@dataclass
class FakeRetriever:
    results: list[SearchResult] = field(default_factory=list)
    error: Exception | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        title: str | None = None,
    ) -> list[SearchResult]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "document_id": document_id,
                "title": title,
            }
        )
        if self.error:
            raise self.error
        return self.results


@dataclass
class FakeLLM(LanguageModelProvider):
    response: str = "Resposta fundamentada [Fonte 1]."
    error: Exception | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error:
            raise self.error
        return self.response


def test_answer_uses_retrieved_context_and_returns_sources() -> None:
    retriever = FakeRetriever(
        results=[result("A discalculia afeta a aprendizagem matemática.")]
    )
    llm = FakeLLM()
    service = RAGService(retriever, llm, retrieval_top_k=7)

    response = service.answer(
        "Como a discalculia afeta a aprendizagem?",
        document_id="documento-1",
    )

    assert response.answer == "Resposta fundamentada [Fonte 1]."
    assert response.sources[0].chunk_id == "chunk-1"
    assert response.sources[0].file_name == "tcc.pdf"
    assert response.sources[0].page_start == 3
    assert response.sources[0].score == 0.8
    assert retriever.calls[0]["top_k"] == 7
    assert retriever.calls[0]["document_id"] == "documento-1"
    assert "A discalculia afeta" in str(llm.calls[0]["user_prompt"])
    assert "somente com informações sustentadas" in str(
        llm.calls[0]["system_prompt"]
    )
    assert "sempre em português" in str(llm.calls[0]["system_prompt"])


@pytest.mark.parametrize("question", ["", "   ", "\n"])
def test_empty_question_is_rejected(question: str) -> None:
    with pytest.raises(InvalidQuestionError, match="não pode ser vazia"):
        RAGService(FakeRetriever(), FakeLLM()).answer(question)


def test_question_length_is_limited() -> None:
    with pytest.raises(InvalidQuestionError, match="excede"):
        RAGService(
            FakeRetriever(),
            FakeLLM(),
            max_question_chars=10,
        ).answer("pergunta muito longa")


def test_empty_database_does_not_call_llm() -> None:
    llm = FakeLLM()

    response = RAGService(FakeRetriever(), llm).answer("Pergunta sem documentos")

    assert response.answer == NO_CONTEXT_ANSWER
    assert response.sources == []
    assert response.generation_time_ms == 0
    assert llm.calls == []


def test_irrelevant_results_are_not_sent_to_llm() -> None:
    llm = FakeLLM()
    retriever = FakeRetriever(results=[result("Trecho irrelevante", similarity=0.2)])

    response = RAGService(
        retriever,
        llm,
        min_similarity=0.5,
    ).answer("Pergunta")

    assert response.answer == NO_CONTEXT_ANSWER
    assert response.sources == []
    assert llm.calls == []


def test_near_duplicates_are_removed_and_context_is_limited() -> None:
    original = "A educação matemática promove aprendizagem significativa."
    duplicate = "A educação matemática promove aprendizagem significativa!"
    long_text = "geometria " * 200
    retriever = FakeRetriever(
        results=[
            result(original, chunk_id="a"),
            result(duplicate, chunk_id="b"),
            result(long_text, chunk_id="c", page=4),
        ]
    )
    llm = FakeLLM()

    response = RAGService(
        retriever,
        llm,
        max_context_chars=400,
    ).answer("O que o texto discute?")

    assert [source.chunk_id for source in response.sources] == ["a", "c"]
    prompt = str(llm.calls[0]["user_prompt"])
    context = prompt.split("CONTEXTO RECUPERADO:\n", 1)[1].split(
        "\n\nElabore", 1
    )[0]
    assert len(context) <= 400
    assert "[Fonte 3]" not in context


@pytest.mark.parametrize(
    "error",
    [RuntimeError("falha externa"), LLMTimeoutError("timeout")],
)
def test_llm_failure_is_controlled(error: Exception) -> None:
    llm = FakeLLM(error=error)
    retriever = FakeRetriever(results=[result("Contexto válido")])

    response = RAGService(retriever, llm).answer("Pergunta")

    assert response.answer == GENERATION_FAILURE_ANSWER
    assert len(response.sources) == 1
    assert response.generation_time_ms >= 0


def test_retrieval_failure_is_controlled() -> None:
    llm = FakeLLM()
    retriever = FakeRetriever(error=RuntimeError("Chroma indisponível"))

    response = RAGService(retriever, llm).answer("Pergunta")

    assert response.answer == RETRIEVAL_FAILURE_ANSWER
    assert response.sources == []
    assert llm.calls == []
