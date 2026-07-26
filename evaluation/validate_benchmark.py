"""Validação bloqueante do benchmark aprovado."""

import argparse
from collections import Counter
from pathlib import Path

import pypdfium2 as pdfium

from app.config import get_settings
from evaluation.io import read_benchmark, read_json
from evaluation.models import Benchmark


def validate_benchmark(
    benchmark: Benchmark,
    documents_dir: Path,
    development_run: Path | None = None,
    *,
    require_approved: bool = True,
) -> list[str]:
    errors: list[str] = []
    questions = benchmark.questions
    specifications = {
        "1.0": {"total": 50, "unanswerable": 10, "split": 25},
        "2.0": {"total": 100, "unanswerable": 16, "split": 50},
    }
    specification = specifications.get(benchmark.benchmark_version)
    if specification is None:
        errors.append(f"Versão de benchmark desconhecida: {benchmark.benchmark_version}")
        return errors
    ids = [question.id for question in questions]
    duplicates = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)
    if len(questions) != specification["total"]:
        errors.append(
            f"Total inválido: esperado {specification['total']}, obtido {len(questions)}"
        )
    if duplicates:
        errors.append(f"IDs duplicados: {', '.join(duplicates)}")
    unanswerable = sum(not question.answerable for question in questions)
    if unanswerable != specification["unanswerable"]:
        errors.append(
            "Proporção inválida: esperado "
            f"{specification['unanswerable']}/{specification['total']} sem resposta, "
            f"obtido {unanswerable}/{len(questions)}"
        )
    split_counts = Counter(question.split for question in questions)
    expected_splits = {
        "development": specification["split"],
        "final": specification["split"],
    }
    if split_counts != expected_splits:
        errors.append(f"Divisão inválida: {dict(split_counts)}")
    if require_approved:
        not_approved = [question.id for question in questions if question.status != "approved"]
        if not_approved:
            errors.append(f"Perguntas não aprovadas: {', '.join(not_approved)}")

    page_counts: dict[str, int] = {}
    for question in questions:
        if question.answerable:
            if not question.evidence.strip():
                errors.append(f"{question.id}: evidência vazia")
            if not question.expected_document or not question.expected_pages:
                errors.append(f"{question.id}: fonte obrigatória ausente")
                continue
            path = documents_dir / question.expected_document
            if not path.is_file():
                errors.append(f"{question.id}: documento inexistente: {question.expected_document}")
                continue
            if question.expected_document not in page_counts:
                try:
                    document = pdfium.PdfDocument(path)
                    page_counts[question.expected_document] = len(document)
                    document.close()
                except Exception as exc:
                    errors.append(f"{question.id}: PDF ilegível ({type(exc).__name__})")
                    continue
            invalid_pages = [page for page in question.expected_pages if page < 1 or page > page_counts[question.expected_document]]
            if invalid_pages:
                errors.append(f"{question.id}: páginas fora do PDF: {invalid_pages}")
        else:
            if question.expected_document is not None or question.expected_pages:
                errors.append(f"{question.id}: pergunta sem resposta contém fonte")
            if not question.unanswerable_reason:
                errors.append(f"{question.id}: motivo de ausência não informado")

    if benchmark.benchmark_version == "2.0":
        corpus = {path.name for path in documents_dir.glob("*.pdf")}
        excluded = set(benchmark.excluded_documents)
        if len(excluded) != 1:
            errors.append(
                f"Benchmark 2.0 exige uma exclusão documental justificada; obtidas {len(excluded)}"
            )
        unknown_exclusions = sorted(excluded - corpus)
        if unknown_exclusions:
            errors.append(f"Exclusões fora do corpus: {', '.join(unknown_exclusions)}")
        for split in ("development", "final"):
            represented = Counter(
                question.expected_document
                for question in questions
                if question.split == split and question.answerable
            )
            missing = sorted(corpus - excluded - set(represented))
            repeated = sorted(name for name, count in represented.items() if count != 1)
            if missing:
                errors.append(f"{split}: TCCs sem pergunta: {', '.join(missing)}")
            if repeated:
                errors.append(f"{split}: TCCs sem cobertura unitária: {', '.join(repeated)}")
            included_exclusions = sorted(excluded & set(represented))
            if included_exclusions:
                errors.append(
                    f"{split}: documentos excluídos possuem perguntas: "
                    f"{', '.join(included_exclusions)}"
                )

    if development_run:
        payload = read_json(development_run)
        final_ids = {question.id for question in questions if question.split == "final"}
        used = {str(record.get("id")) for record in payload.get("records", [])}
        leaked = sorted(final_ids & used)
        if leaked:
            errors.append(f"Perguntas finais encontradas em execução de desenvolvimento: {', '.join(leaked)}")
    return errors


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Valida o benchmark aprovado")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--documents-dir", type=Path, default=settings.documents_dir)
    parser.add_argument("--development-run", type=Path)
    args = parser.parse_args()
    benchmark = read_benchmark(args.benchmark)
    errors = validate_benchmark(benchmark, args.documents_dir, args.development_run)
    if errors:
        for error in errors:
            print(f"ERRO: {error}")
        raise SystemExit(1)
    print(
        f"Benchmark válido: {len(benchmark.questions)} perguntas aprovadas, "
        "fontes e splits conferidos."
    )


if __name__ == "__main__":
    main()
