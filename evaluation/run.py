"""Executa perguntas aprovadas contra as APIs públicas do chatbot."""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.rag.grounding import is_refusal
from evaluation.configuration import (
    benchmark_fingerprint,
    code_revision,
    configuration_fingerprint,
    runtime_versions,
    safe_settings,
    validate_runtime_configuration,
    working_tree_provenance,
)
from evaluation.io import read_benchmark, read_json, write_json
from evaluation.models import PreflightRecord, RunOutput, RunRecord
from evaluation.validate_benchmark import validate_benchmark
from frontend.api_client import APIClient, APIClientError, APITimeoutError


def _pages(results: list[dict[str, Any]]) -> list[int]:
    pages: list[int] = []
    for result in results:
        start = result.get("page_start")
        end = result.get("page_end") or start
        if isinstance(start, int) and isinstance(end, int):
            pages.extend(range(start, end + 1))
    return list(dict.fromkeys(pages))


def execute_question(client: APIClient, question, split: str, settings: dict[str, Any]) -> RunRecord:
    started = time.perf_counter()
    answer = ""
    chat: dict[str, Any] = {}
    search: dict[str, Any] = {}
    error: str | None = None
    timeout = False
    try:
        chat = client.chat(question.question, top_k=int(settings["top_k"]))
        answer = str(chat.get("answer", ""))
        search = client.search(question.question, top_k=int(settings["top_k"]))
    except APITimeoutError as exc:
        timeout = True
        error = f"{type(exc).__name__}: {exc}"
    except APIClientError as exc:
        error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        error = f"{type(exc).__name__}: falha inesperada"
    results = search.get("results", []) if isinstance(search, dict) else []
    sources = chat.get("sources", []) if isinstance(chat, dict) else []
    context = chat.get("retrieved_context", []) if isinstance(chat, dict) else []
    selection_trace = chat.get("selection_trace", []) if isinstance(chat, dict) else []
    return RunRecord(
        id=question.id, question=question.question, answerable=question.answerable,
        question_type=question.question_type, difficulty=question.difficulty,
        expected_answer=question.expected_answer, required_facts=question.required_facts,
        produced_answer=answer, expected_document=question.expected_document,
        expected_pages=question.expected_pages,
        retrieved_documents=[str(result.get("file_name", "")) for result in results],
        retrieved_pages=_pages(results),
        similarities=[float(result.get("score", 0.0)) for result in results],
        returned_passages=[str(result.get("content", "")) for result in results],
        retrieval_results=list(results),
        context_results=list(context),
        context_documents=[str(source.get("file_name", "")) for source in context],
        context_pages=_pages(context),
        sources=list(sources), top_k=int(settings["top_k"]),
        selection_trace=list(selection_trace),
        similarity_threshold=float(settings["similarity_threshold"]),
        total_time_ms=max(0, round((time.perf_counter() - started) * 1000)),
        retrieval_time_ms=search.get("retrieval_time_ms") if search else chat.get("retrieval_time_ms"),
        generation_time_ms=chat.get("generation_time_ms"), refused=is_refusal(answer),
        error=error, timeout=timeout, timestamp=datetime.now(timezone.utc).isoformat(),
        split=split, settings=settings,
    )


def approved_preflight(
    execution_settings: dict[str, Any],
    health: dict[str, Any],
    benchmark_version: str,
    benchmark_sha256: str,
) -> PreflightRecord:
    """Valida e materializa o preflight; nunca retorna um registro reprovado."""
    actual = dict(health.get("configuration") or {})
    runtime_errors = validate_runtime_configuration(execution_settings, actual)
    configuration_match = not runtime_errors
    corpus_match = actual.get("corpus") == execution_settings.get("corpus")
    benchmark_match = (
        execution_settings.get("benchmark_version") == benchmark_version
        and execution_settings.get("benchmark_fingerprint") == benchmark_sha256
    )
    health_status = str(health.get("status", ""))
    failures: list[str] = []
    if health_status != "ok":
        failures.append(f"health_status={health_status!r}")
    if not configuration_match:
        failures.extend(runtime_errors)
    if not corpus_match:
        failures.append("fingerprint do corpus divergente")
    if not benchmark_match:
        failures.append("versão ou fingerprint do benchmark divergente")
    if failures:
        raise ValueError(
            "Preflight reprovado; a avaliação não foi iniciada: "
            + "; ".join(dict.fromkeys(failures))
        )
    corpus = dict(execution_settings.get("corpus") or {})
    return PreflightRecord(
        passed=True,
        checked_at=datetime.now(timezone.utc).isoformat(),
        health_status=health_status,
        configuration_match=True,
        corpus_match=True,
        benchmark_match=True,
        configuration_fingerprint=str(
            execution_settings.get("configuration_fingerprint", "unknown")
        ),
        corpus_fingerprint=str(corpus.get("sha256", "unknown")),
        benchmark_version=benchmark_version,
        benchmark_fingerprint=benchmark_sha256,
        code_revision=str(execution_settings.get("code_revision", "unknown")),
        working_tree=dict(execution_settings.get("working_tree") or {}),
        runtime_versions=dict(execution_settings.get("runtime_versions") or {}),
    )


def validate_frozen_benchmark_identity(
    execution_settings: dict[str, Any],
    benchmark_version: str,
    benchmark_sha256: str,
) -> None:
    """Bloqueia o uso de um benchmark diferente antes de qualquer chamada à API."""
    if execution_settings.get("benchmark_version") != benchmark_version:
        raise ValueError("Versão do benchmark difere da configuração congelada")
    expected_fingerprint = execution_settings.get("benchmark_fingerprint")
    if not expected_fingerprint:
        raise ValueError("Configuração congelada não contém fingerprint do benchmark")
    if expected_fingerprint != benchmark_sha256:
        raise ValueError("Fingerprint do benchmark difere da configuração congelada")


def run_benchmark(
    benchmark_path: Path,
    split: str,
    output_path: Path,
    base_url: str,
    timeout_seconds: float,
    confirm_final: bool = False,
    frozen_path: Path = Path("evaluation/config/frozen_config.json"),
) -> RunOutput:
    if split == "final" and not confirm_final:
        raise ValueError("O split final exige --confirm-final")
    benchmark_sha256 = benchmark_fingerprint(benchmark_path)
    benchmark = read_benchmark(benchmark_path)
    if split == "final":
        if not frozen_path.is_file():
            raise ValueError("O split final exige evaluation/config/frozen_config.json")
        execution_settings = read_json(frozen_path)
        if execution_settings.get("status") != "frozen":
            raise ValueError("A configuração final ainda não foi congelada com evaluation.freeze_config")
        validate_frozen_benchmark_identity(
            execution_settings,
            benchmark.benchmark_version,
            benchmark_sha256,
        )
    app_settings = get_settings()
    validation_errors = validate_benchmark(benchmark, app_settings.documents_dir)
    if validation_errors:
        raise ValueError("Benchmark inválido: " + "; ".join(validation_errors))
    if split != "final":
        configuration = safe_settings(app_settings)
        execution_settings = {
            **configuration,
            "configuration_fingerprint": configuration_fingerprint(configuration),
            "benchmark_version": benchmark.benchmark_version,
            "benchmark_fingerprint": benchmark_sha256,
            "seed": benchmark.seed,
            "code_revision": code_revision(),
            "working_tree": working_tree_provenance(),
            "runtime_versions": runtime_versions(),
        }
    execution_settings = {**execution_settings, "api_base_url": base_url, "client_timeout_seconds": timeout_seconds}
    selected = [question for question in benchmark.questions if question.split == split and question.status == "approved"]
    started_at = datetime.now(timezone.utc).isoformat()
    client = APIClient(base_url, default_timeout=timeout_seconds, chat_timeout=timeout_seconds)
    try:
        try:
            health = client.health()
        except APIClientError as exc:
            raise ValueError(
                "Não foi possível validar a configuração da API antes da avaliação"
            ) from exc
        preflight = approved_preflight(
            execution_settings,
            health,
            benchmark.benchmark_version,
            benchmark_sha256,
        )
        records = [execute_question(client, question, split, execution_settings) for question in selected]
    finally:
        client.close()
    output = RunOutput(
        benchmark_version=benchmark.benchmark_version, split=split,
        started_at=started_at, completed_at=datetime.now(timezone.utc).isoformat(),
        settings=execution_settings, preflight=preflight, records=records,
    )
    write_json(output_path, output.model_dump(mode="json"))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o benchmark pela API")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "final"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--confirm-final", action="store_true")
    parser.add_argument("--frozen-config", type=Path, default=Path("evaluation/config/frozen_config.json"))
    args = parser.parse_args()
    try:
        result = run_benchmark(args.benchmark, args.split, args.output, args.api_base_url, args.timeout, args.confirm_final, args.frozen_config)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Executadas {len(result.records)} perguntas do split {args.split}; saída em {args.output}")


if __name__ == "__main__":
    main()
