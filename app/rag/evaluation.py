"""Saída de avaliação do RAG, separada do contrato HTTP público."""

from pydantic import BaseModel

from app.rag.models import RAGResponse, RAGTimings


class EvaluationOutput(BaseModel):
    request_id: str | None
    status: str
    source_count: int
    context_chars: int
    error_type: str | None
    durations: RAGTimings


def build_evaluation_output(response: RAGResponse) -> EvaluationOutput:
    """Converte uma resposta interna nas métricas consumidas pela avaliação."""
    if response.observation is not None:
        observation = response.observation
        return EvaluationOutput(
            request_id=observation.request_id,
            status=observation.status,
            source_count=observation.source_count,
            context_chars=observation.context_chars,
            error_type=observation.error_type,
            durations=observation.timings,
        )
    return EvaluationOutput(
        request_id=None,
        status="unknown",
        source_count=len(response.sources),
        context_chars=0,
        error_type=None,
        durations=RAGTimings(
            generation_time_ms=response.generation_time_ms,
            total_time_ms=response.retrieval_time_ms + response.generation_time_ms,
        ),
    )
