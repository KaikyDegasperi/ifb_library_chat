"""Métricas determinísticas de recuperação, citação, recusa e operação."""

import math
import statistics
from collections.abc import Iterable
from typing import Any


def _answerable(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("answerable")]


def document_recall_at(records: Iterable[dict[str, Any]], k: int) -> float:
    items = _answerable(records)
    if not items:
        return 0.0
    hits = sum(record.get("expected_document") in record.get("retrieved_documents", [])[:k] for record in items)
    return hits / len(items)


def page_recall_at(records: Iterable[dict[str, Any]], k: int) -> float:
    items = _answerable(records)
    if not items:
        return 0.0
    hits = 0
    for record in items:
        expected = set(record.get("expected_pages", []))
        pages: set[int] = set()
        for result in record.get("retrieval_results", [])[:k]:
            start = result.get("page_start")
            end = result.get("page_end") or start
            if isinstance(start, int) and isinstance(end, int):
                pages.update(range(start, end + 1))
        hits += bool(expected & pages)
    return hits / len(items)


def mean_reciprocal_rank(records: Iterable[dict[str, Any]]) -> float:
    items = _answerable(records)
    if not items:
        return 0.0
    total = 0.0
    for record in items:
        expected = record.get("expected_document")
        try:
            rank = record.get("retrieved_documents", []).index(expected) + 1
        except ValueError:
            continue
        total += 1 / rank
    return total / len(items)


def _citation_hit(record: dict[str, Any], page: bool = False) -> bool:
    for source in record.get("sources", []):
        if source.get("file_name") != record.get("expected_document"):
            continue
        if not page:
            return True
        start = source.get("page_start")
        end = source.get("page_end") or start
        if isinstance(start, int) and isinstance(end, int) and set(range(start, end + 1)) & set(record.get("expected_pages", [])):
            return True
    return False


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return float(ordered[index])


def calculate_metrics(records: list[dict[str, Any]], top_k: int | None = None) -> dict[str, Any]:
    answerables = _answerable(records)
    unanswerables = [record for record in records if not record.get("answerable")]
    effective_k = top_k or max((int(record.get("top_k", 0)) for record in records), default=0)
    times = [float(record.get("total_time_ms", 0)) for record in records]
    cited_document = sum(_citation_hit(record) for record in answerables)
    cited_page = sum(_citation_hit(record, page=True) for record in answerables)
    correct_refusals = sum(bool(record.get("refused")) for record in unanswerables)
    improper_refusals = sum(bool(record.get("refused")) for record in answerables)
    improper_answers = sum(not bool(record.get("refused")) for record in unanswerables)
    return {
        "question_count": len(records),
        "answerable_count": len(answerables),
        "unanswerable_count": len(unanswerables),
        "document_recall_at_1": document_recall_at(records, 1),
        "document_recall_at_3": document_recall_at(records, 3),
        "document_recall_at_k": document_recall_at(records, effective_k),
        "page_recall_at_k": page_recall_at(records, effective_k),
        "mrr": mean_reciprocal_rank(records),
        "correct_document_citation_rate": _rate(cited_document, len(answerables)),
        "correct_page_citation_rate": _rate(cited_page, len(answerables)),
        "correct_refusal_rate": _rate(correct_refusals, len(unanswerables)),
        "improper_refusal_rate": _rate(improper_refusals, len(answerables)),
        "improper_answer_rate": _rate(improper_answers, len(unanswerables)),
        "mean_time_ms": statistics.fmean(times) if times else 0.0,
        "median_time_ms": statistics.median(times) if times else 0.0,
        "p95_time_ms": percentile(times, 0.95),
        "error_count": sum(bool(record.get("error")) for record in records),
        "timeout_count": sum(bool(record.get("timeout")) for record in records),
    }


def grouped_metrics(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(str(record.get(field, "não informado")), []).append(record)
    return {name: calculate_metrics(items) for name, items in sorted(groups.items())}
