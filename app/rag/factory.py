"""Fábricas que conectam configuração e provedores concretos."""

from app.config import Settings
from app.rag.llm import (
    LanguageModelProvider,
    OllamaChatProvider,
    OpenAICompatibleProvider,
    UnavailableLLMProvider,
)
from app.rag.service import RAGService
from app.vectorstore import SentenceTransformerProvider, VectorIndexService


def create_llm_provider(settings: Settings) -> LanguageModelProvider:
    provider = settings.llm_provider.strip().lower()
    if provider == "none":
        return UnavailableLLMProvider()
    if provider in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url or "",
            model=settings.llm_model or "",
            api_key=settings.llm_api_key,
            default_temperature=settings.local_llm_temperature,
            default_top_p=settings.local_llm_top_p,
            default_max_tokens=settings.local_llm_max_tokens,
        )
    if provider in {"ollama", "ollama-compatible", "local-llm", "local_llm"}:
        return OllamaChatProvider(
            base_url=settings.llm_base_url or "",
            model=settings.llm_model or "",
            api_key=settings.llm_api_key,
            default_temperature=settings.local_llm_temperature,
            default_top_p=settings.local_llm_top_p,
            default_max_tokens=settings.local_llm_max_tokens,
            default_context_window=settings.local_llm_context_size,
            keep_alive=settings.local_llm_keep_alive or None,
        )
    raise ValueError(f"Provedor de LLM não suportado: {settings.llm_provider}")


def create_rag_service(settings: Settings) -> RAGService:
    embedding_provider = SentenceTransformerProvider(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    )
    retriever = VectorIndexService(
        persist_dir=settings.chroma_dir,
        collection_name=settings.chroma_collection,
        embedding_provider=embedding_provider,
        batch_size=settings.embedding_batch_size,
    )
    return RAGService(
        retriever=retriever,
        llm_provider=create_llm_provider(settings),
        retrieval_top_k=settings.rag_retrieval_top_k,
        candidate_pool_size=settings.rag_candidate_pool_size,
        min_similarity=settings.rag_min_similarity,
        max_context_chars=settings.rag_max_context_chars,
        max_question_chars=settings.rag_max_question_chars,
        duplicate_threshold=settings.rag_duplicate_threshold,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        metrics_details_enabled=settings.metrics_details_enabled,
    )
