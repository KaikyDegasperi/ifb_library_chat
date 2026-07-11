"""Erros controlados do pipeline RAG."""


class RAGError(Exception):
    """Erro-base do pipeline."""


class InvalidQuestionError(RAGError, ValueError):
    """Pergunta vazia ou maior que o limite configurado."""


class LLMProviderError(RAGError):
    """Falha retornada pelo provedor de linguagem."""


class LLMTimeoutError(LLMProviderError):
    """Tempo limite excedido ao gerar a resposta."""
