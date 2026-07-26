import json
from pathlib import Path

import pytest

from evaluation.generate_benchmark import generate_benchmark, generate_corpus_benchmark
from evaluation.io import (
    benchmark_from_xlsx,
    read_benchmark,
    write_benchmark,
    write_benchmark_xlsx,
)
from evaluation.metrics import document_recall_at, mean_reciprocal_rank, page_recall_at
from evaluation.models import Benchmark, BenchmarkQuestion, RunOutput, RunRecord
from evaluation.report import generate_reports
from evaluation.run import execute_question, is_refusal, run_benchmark
from evaluation.validate_benchmark import validate_benchmark
from frontend.api_client import APIClientError, APITimeoutError


def question(index: int, *, answerable: bool = True, split: str | None = None) -> BenchmarkQuestion:
    return BenchmarkQuestion(
        id=f"Q{index:03d}", question=f"Pergunta {index}?", answerable=answerable,
        question_type="metodologia" if answerable else "pergunta sem resposta no acervo",
        difficulty="media", expected_answer="Resposta esperada" if answerable else "Deve recusar",
        required_facts=["fato"], expected_document="doc.pdf" if answerable else None,
        expected_pages=[1] if answerable else [], evidence="evidência" if answerable else "",
        split=split or ("development" if index <= 25 else "final"), status="approved",
        rationale="teste", unanswerable_reason=None if answerable else "fora do acervo",
    )


def valid_benchmark() -> Benchmark:
    items = []
    for index in range(1, 51):
        # Cinco negativas em cada split.
        answerable = index not in {*range(21, 26), *range(46, 51)}
        items.append(question(index, answerable=answerable))
    return Benchmark(seed=42, questions=items)


def record(identifier: str = "Q001", **changes) -> dict:
    value = {
        "id": identifier, "question": "q", "answerable": True,
        "question_type": "factual", "difficulty": "facil", "expected_answer": "a",
        "required_facts": ["a"], "produced_answer": "a", "expected_document": "doc.pdf",
        "expected_pages": [2], "retrieved_documents": ["other.pdf", "doc.pdf"],
        "retrieved_pages": [9, 2], "similarities": [0.9, 0.8], "returned_passages": ["x", "a"],
        "retrieval_results": [
            {"file_name": "other.pdf", "page_start": 9, "page_end": 9},
            {"file_name": "doc.pdf", "page_start": 2, "page_end": 2},
        ],
        "sources": [{"file_name": "doc.pdf", "page_start": 2, "page_end": 2}],
        "top_k": 2, "similarity_threshold": 0.35, "total_time_ms": 10,
        "retrieval_time_ms": 4, "generation_time_ms": 6, "refused": False,
        "error": None, "timeout": False, "timestamp": "2026-01-01T00:00:00+00:00",
        "split": "development", "settings": {},
    }
    value.update(changes)
    return value


def test_benchmark_round_trip(tmp_path: Path):
    path = tmp_path / "benchmark.json"
    expected = valid_benchmark()
    write_benchmark(path, expected)
    assert read_benchmark(path) == expected


def test_generation_has_exact_distribution_and_pending_status(tmp_path: Path):
    for index in range(40):
        metadata = {
            "file_name": f"doc-{index}.pdf", "title": f"Trabalho {index}",
            "page_start": 2, "page_end": 2, "section": "Metodologia",
        }
        payload = {"chunks": [{"text": "Metodologia " + ("A pesquisa analisou dados acadêmicos por meio de questionários. " * 8), "metadata": metadata}]}
        (tmp_path / f"{index}.chunks.json").write_text(json.dumps(payload), encoding="utf-8")
    benchmark = generate_benchmark(tmp_path, 50, 0.20, 42)
    assert len(benchmark.questions) == 50
    assert sum(item.answerable for item in benchmark.questions) == 40
    assert sum(item.split == "development" for item in benchmark.questions) == 25
    assert {item.status for item in benchmark.questions} == {"pending_review"}


def test_full_corpus_benchmark_covers_each_document_in_both_splits(tmp_path: Path):
    documents_dir = tmp_path / "pdfs"
    processed_dir = tmp_path / "processed"
    documents_dir.mkdir()
    processed_dir.mkdir()
    for index in range(43):
        name = f"doc-{index:02d}.pdf"
        (documents_dir / name).write_bytes(b"%PDF-1.4")
        chunks = []
        pages = (2,) if index == 42 else (2, 3)
        for page in pages:
            chunks.append(
                {
                    "text": "Metodologia " + (
                        f"O trabalho {index} analisou dados educacionais na página {page}. "
                        * 8
                    ),
                    "metadata": {
                        "file_name": name,
                        "title": f"Trabalho {index}",
                        "page_start": page,
                        "page_end": page,
                        "section": "Metodologia",
                    },
                }
            )
        (processed_dir / f"{index}.chunks.json").write_text(
            json.dumps({"chunks": chunks}), encoding="utf-8"
        )

    benchmark = generate_corpus_benchmark(processed_dir, seed=42)

    assert benchmark.benchmark_version == "2.0"
    assert len(benchmark.questions) == 100
    assert sum(question.answerable for question in benchmark.questions) == 84
    assert "doc-42.pdf" in benchmark.excluded_documents
    for split in ("development", "final"):
        represented = {
            question.expected_document
            for question in benchmark.questions
            if question.split == split and question.answerable
        }
        assert represented == {f"doc-{index:02d}.pdf" for index in range(42)}

    xlsx = tmp_path / "benchmark.xlsx"
    write_benchmark_xlsx(xlsx, benchmark, documents_dir)
    restored = benchmark_from_xlsx(xlsx)
    assert restored.benchmark_version == "2.0"
    assert restored.seed == 42
    assert restored.excluded_documents == benchmark.excluded_documents
    assert len(restored.questions) == 100


def test_validation_detects_missing_documents_and_unapproved(tmp_path: Path):
    benchmark = valid_benchmark()
    benchmark.questions[0].status = "pending_review"
    errors = validate_benchmark(benchmark, tmp_path)
    assert any("não aprovadas" in error for error in errors)
    assert any("documento inexistente" in error for error in errors)


def test_validation_detects_page_outside_pdf(tmp_path: Path, monkeypatch):
    class FakePdf:
        def __len__(self):
            return 2

        def close(self):
            pass

    (tmp_path / "doc.pdf").touch()
    monkeypatch.setattr("evaluation.validate_benchmark.pdfium.PdfDocument", lambda path: FakePdf())
    benchmark = valid_benchmark()
    benchmark.questions[0].expected_pages = [3]
    errors = validate_benchmark(benchmark, tmp_path)
    assert any("Q001" in error and "páginas fora" in error for error in errors)


def test_validation_detects_final_leakage(tmp_path: Path):
    benchmark = valid_benchmark()
    development_run = tmp_path / "run.json"
    development_run.write_text('{"records":[{"id":"Q026"}]}', encoding="utf-8")
    errors = validate_benchmark(benchmark, tmp_path, development_run, require_approved=False)
    assert any("Q026" in error and "finais" in error for error in errors)


def test_recall_mrr_and_page_metrics():
    records = [record()]
    assert document_recall_at(records, 1) == 0
    assert document_recall_at(records, 2) == 1
    assert mean_reciprocal_rank(records) == 0.5
    assert page_recall_at(records, 1) == 0
    assert page_recall_at(records, 2) == 1


def test_page_recall_requires_the_expected_document():
    records = [
        record(
            retrieved_documents=["other.pdf"],
            retrieval_results=[
                {"file_name": "other.pdf", "page_start": 2, "page_end": 2}
            ],
            top_k=1,
        )
    ]
    assert page_recall_at(records, 1) == 0


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Não encontrei essa informação no acervo.", True),
        ("Com base nas fontes consultadas, não encontrei essa informação.", True),
        ("A resposta é 42.", False),
        (
            "A resposta fundamentada está aqui e apresenta todos os fatos solicitados. "
            "Em uma ressalva posterior, não encontrei informações adicionais.",
            False,
        ),
    ],
)
def test_refusal_classification(answer: str, expected: bool):
    assert is_refusal(answer) is expected


class FakeClient:
    def __init__(self, exception):
        self.exception = exception

    def chat(self, *args, **kwargs):
        raise self.exception


def test_timeout_is_recorded():
    result = execute_question(
        FakeClient(APITimeoutError("timeout")), question(1), "development",
        {"top_k": 5, "similarity_threshold": 0.35},
    )
    assert result.timeout is True
    assert "APITimeoutError" in result.error


def test_api_error_is_recorded():
    result = execute_question(
        FakeClient(APIClientError("erro")), question(1), "development",
        {"top_k": 5, "similarity_threshold": 0.35},
    )
    assert result.timeout is False
    assert "APIClientError" in result.error


def test_final_requires_confirmation(tmp_path: Path):
    with pytest.raises(ValueError, match="confirm-final"):
        run_benchmark(tmp_path / "missing.json", "final", tmp_path / "out.json", "http://api", 1)


def test_final_requires_frozen_config(tmp_path: Path, monkeypatch):
    benchmark_path = tmp_path / "benchmark.json"
    write_benchmark(benchmark_path, valid_benchmark())
    monkeypatch.setattr("evaluation.run.validate_benchmark", lambda *args, **kwargs: [])
    with pytest.raises(ValueError, match="frozen_config"):
        run_benchmark(
            benchmark_path, "final", tmp_path / "out.json", "http://api", 1,
            confirm_final=True, frozen_path=tmp_path / "missing-frozen.json",
        )


def test_report_generation(tmp_path: Path):
    run = RunOutput(
        benchmark_version="1.0", split="development",
        started_at="2026-01-01T00:00:00+00:00", completed_at="2026-01-01T00:01:00+00:00",
        settings={"top_k": 2}, records=[RunRecord.model_validate(record())],
    )
    run_path = tmp_path / "run.json"
    run_path.write_text(run.model_dump_json(), encoding="utf-8")
    report = generate_reports(run_path, tmp_path / "reports")
    assert report["metrics"]["document_recall_at_k"] == 1
    for suffix in ("json", "csv", "xlsx", "html"):
        assert (tmp_path / "reports" / f"report.{suffix}").is_file()
