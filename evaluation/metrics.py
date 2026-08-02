"""Métricas determinísticas de recuperação, citação, recusa e operação."""

import math
import re
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


def context_recall_at(records: Iterable[dict[str, Any]], k: int) -> float:
    items = _answerable(records)
    if not items:
        return 0.0
    hits = sum(
        record.get("expected_document")
        in record.get("context_documents", [])[:k]
        for record in items
    )
    return hits / len(items)


def page_recall_at(records: Iterable[dict[str, Any]], k: int) -> float:
    items = _answerable(records)
    if not items:
        return 0.0
    hits = 0
    for record in items:
        expected = set(record.get("expected_pages", []))
        expected_document = record.get("expected_document")
        pages: set[int] = set()
        for result in record.get("retrieval_results", [])[:k]:
            if result.get("file_name") != expected_document:
                continue
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


def context_mean_reciprocal_rank(records: Iterable[dict[str, Any]]) -> float:
    items = _answerable(records)
    if not items:
        return 0.0
    total = 0.0
    for record in items:
        try:
            rank = record.get("context_documents", []).index(
                record.get("expected_document")
            ) + 1
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
    true_positives = sum(not bool(record.get("refused")) for record in answerables)
    false_negatives = improper_refusals
    false_positives = improper_answers
    true_negatives = correct_refusals
    precision = _rate(true_positives, true_positives + false_positives)
    recall = _rate(true_positives, true_positives + false_negatives)
    f1 = _rate(2 * precision * recall, precision + recall)
    citation_pattern = re.compile(r"\[Fonte\s+(\d+)\]", re.IGNORECASE)
    with_inline_source = 0
    with_valid_inline_source = 0
    expected_document_cited = 0
    unrelated_expected_document_citations = 0
    correct_refusal_without_sources = 0
    answered_count = 0
    for record in records:
        sources = list(record.get("sources", []))
        indices = [
            int(value)
            for value in citation_pattern.findall(str(record.get("produced_answer") or ""))
        ]
        valid_indices = [index for index in indices if 1 <= index <= len(sources)]
        answered = not bool(record.get("refused"))
        if answered:
            answered_count += 1
            with_inline_source += bool(indices)
            with_valid_inline_source += bool(valid_indices)
        if record.get("answerable") and answered:
            cited = [sources[index - 1] for index in valid_indices]
            expected = record.get("expected_document")
            expected_document_cited += any(
                source.get("file_name") == expected for source in cited
            )
            unrelated_expected_document_citations += bool(cited) and all(
                source.get("file_name") != expected for source in cited
            )
        elif record.get("refused") and not sources and not indices:
            correct_refusal_without_sources += 1
    return {
        "question_count": len(records),
        "answerable_count": len(answerables),
        "unanswerable_count": len(unanswerables),
        "document_recall_at_1": document_recall_at(records, 1),
        "document_recall_at_3": document_recall_at(records, 3),
        "document_recall_at_k": document_recall_at(records, effective_k),
        "context_recall_at_k": context_recall_at(records, effective_k),
        "page_recall_at_k": page_recall_at(records, effective_k),
        "mrr": mean_reciprocal_rank(records),
        "context_mrr": context_mean_reciprocal_rank(records),
        "retrieval_failure_count": sum(
            record.get("expected_document")
            not in record.get("retrieved_documents", [])[:effective_k]
            for record in answerables
        ),
        "context_failure_count": sum(
            record.get("expected_document")
            not in record.get("context_documents", [])[:effective_k]
            for record in answerables
        ),
        "correct_document_citation_rate": _rate(cited_document, len(answerables)),
        "correct_page_citation_rate": _rate(cited_page, len(answerables)),
        "correct_refusal_rate": _rate(correct_refusals, len(unanswerables)),
        "improper_refusal_rate": _rate(improper_refusals, len(answerables)),
        "improper_answer_rate": _rate(improper_answers, len(unanswerables)),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
        "decision_accuracy": _rate(
            true_positives + true_negatives,
            len(records),
        ),
        "decision_precision": precision,
        "decision_recall": recall,
        "decision_f1": f1,
        "always_answer_accuracy": _rate(len(answerables), len(records)),
        "always_answer_precision": _rate(len(answerables), len(records)),
        "always_answer_recall": 1.0 if answerables else 0.0,
        "always_answer_f1": _rate(
            2 * _rate(len(answerables), len(records)),
            1 + _rate(len(answerables), len(records)),
        ),
        "answer_with_inline_source_count": with_inline_source,
        "answer_with_valid_inline_source_count": with_valid_inline_source,
        "answer_without_inline_source_count": answered_count - with_inline_source,
        "expected_document_cited_count": expected_document_cited,
        "only_non_expected_documents_cited_count": unrelated_expected_document_citations,
        "correct_refusal_without_sources_count": correct_refusal_without_sources,
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
