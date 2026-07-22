"""Executa perguntas aprovadas contra as APIs públicas do chatbot."""

import argparse
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from evaluation.configuration import safe_settings
from evaluation.io import read_benchmark, read_json, write_json
from evaluation.models import RunOutput, RunRecord
from evaluation.validate_benchmark import validate_benchmark
from frontend.api_client import APIClient, APIClientError, APITimeoutError


REFUSAL_PATTERN = re.compile(
    r"(?i)(n[aã]o (?:encontrei|foi poss[ií]vel encontrar|consta|h[aá])|"
    r"informa[cç][aã]o (?:n[aã]o|insuficiente)|n[aã]o est[aá] (?:dispon[ií]vel|no acervo))"
)


def is_refusal(answer: str) -> bool:
    return bool(REFUSAL_PATTERN.search(answer))


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
        sources=list(sources), top_k=int(settings["top_k"]),
        similarity_threshold=float(settings["similarity_threshold"]),
        total_time_ms=max(0, round((time.perf_counter() - started) * 1000)),
        retrieval_time_ms=search.get("retrieval_time_ms") if search else chat.get("retrieval_time_ms"),
        generation_time_ms=chat.get("generation_time_ms"), refused=is_refusal(answer),
        error=error, timeout=timeout, timestamp=datetime.now(timezone.utc).isoformat(),
        split=split, settings=settings,
    )


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
    benchmark = read_benchmark(benchmark_path)
    app_settings = get_settings()
    validation_errors = validate_benchmark(benchmark, app_settings.documents_dir)
    if validation_errors:
        raise ValueError("Benchmark inválido: " + "; ".join(validation_errors))
    if split == "final":
        if not frozen_path.is_file():
            raise ValueError("O split final exige evaluation/config/frozen_config.json")
        execution_settings = read_json(frozen_path)
        if execution_settings.get("status") != "frozen":
            raise ValueError("A configuração final ainda não foi congelada com evaluation.freeze_config")
        if execution_settings.get("benchmark_version") != benchmark.benchmark_version:
            raise ValueError("Versão do benchmark difere da configuração congelada")
    else:
        execution_settings = {
            **safe_settings(app_settings),
            "benchmark_version": benchmark.benchmark_version,
            "seed": benchmark.seed,
        }
    execution_settings = {**execution_settings, "api_base_url": base_url, "client_timeout_seconds": timeout_seconds}
    selected = [question for question in benchmark.questions if question.split == split and question.status == "approved"]
    started_at = datetime.now(timezone.utc).isoformat()
    client = APIClient(base_url, default_timeout=timeout_seconds, chat_timeout=timeout_seconds)
    try:
        records = [execute_question(client, question, split, execution_settings) for question in selected]
    finally:
        client.close()
    output = RunOutput(
        benchmark_version=benchmark.benchmark_version, split=split,
        started_at=started_at, completed_at=datetime.now(timezone.utc).isoformat(),
        settings=execution_settings, records=records,
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
