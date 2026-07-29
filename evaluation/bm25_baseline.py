"""Baseline lexical BM25 para comparação com a recuperação densa.

O baseline reutiliza exatamente os chunks já produzidos pela ingestão. Dessa forma,
a única variável alterada no experimento é o método de ranqueamento.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.io import read_json


TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokeniza texto em termos Unicode, sem stemming ou lista de stopwords."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_PATTERN.findall(normalized)


def _normalized_name(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


@dataclass(frozen=True)
class CorpusChunk:
    chunk_id: str
    content: str
    file_name: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int


class BM25Index:
    """Implementação determinística do BM25 de Okapi sobre chunks."""

    def __init__(
        self,
        chunks: list[CorpusChunk],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if not chunks:
            raise ValueError("O corpus BM25 não pode ser vazio")
        if k1 <= 0:
            raise ValueError("k1 deve ser maior que zero")
        if not 0 <= b <= 1:
            raise ValueError("b deve estar entre zero e um")
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(chunk.content)) for chunk in chunks]
        self.lengths = [sum(frequencies.values()) for frequencies in self.term_frequencies]
        self.average_length = statistics.fmean(self.lengths)
        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for document_index, frequencies in enumerate(self.term_frequencies):
            for term, frequency in frequencies.items():
                postings[term].append((document_index, frequency))
        self.postings = dict(postings)

    def search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("A consulta não pode ser vazia")
        if top_k < 1:
            raise ValueError("top_k deve ser maior que zero")
        scores: dict[int, float] = defaultdict(float)
        corpus_size = len(self.chunks)
        for term in dict.fromkeys(tokenize(query)):
            matches = self.postings.get(term, [])
            document_frequency = len(matches)
            if not document_frequency:
                continue
            inverse_document_frequency = math.log(
                1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            for document_index, term_frequency in matches:
                length_normalization = 1 - self.b + (
                    self.b * self.lengths[document_index] / self.average_length
                )
                scores[document_index] += inverse_document_frequency * (
                    term_frequency * (self.k1 + 1)
                ) / (term_frequency + self.k1 * length_normalization)

        ranked = sorted(
            range(corpus_size),
            key=lambda index: (
                -scores.get(index, 0.0),
                _normalized_name(self.chunks[index].file_name),
                self.chunks[index].chunk_index,
                self.chunks[index].chunk_id,
            ),
        )[: min(top_k, corpus_size)]
        return [
            {
                "rank": rank,
                "chunk_id": self.chunks[index].chunk_id,
                "content": self.chunks[index].content,
                "file_name": self.chunks[index].file_name,
                "page_start": self.chunks[index].page_start,
                "page_end": self.chunks[index].page_end,
                "section": self.chunks[index].section,
                "chunk_index": self.chunks[index].chunk_index,
                "score": scores.get(index, 0.0),
            }
            for rank, index in enumerate(ranked, 1)
        ]


def load_chunks(processed_dir: Path) -> list[CorpusChunk]:
    """Carrega a versão mais recente de cada documento processado."""
    latest: dict[str, tuple[str, Path, dict[str, Any]]] = {}
    for path in sorted(processed_dir.glob("*.chunks.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_chunks = payload.get("chunks", [])
        if not raw_chunks:
            continue
        metadata = raw_chunks[0].get("metadata", {})
        source = str(metadata.get("file_path") or metadata.get("file_name") or path)
        processed_at = str(metadata.get("processed_at") or "")
        current = latest.get(source)
        if current is None or processed_at > current[0]:
            latest[source] = (processed_at, path, payload)

    chunks: list[CorpusChunk] = []
    for _, path, payload in sorted(latest.values(), key=lambda item: str(item[1])):
        for position, item in enumerate(payload.get("chunks", [])):
            metadata = item.get("metadata", {})
            content = str(item.get("text") or "")
            if not content.strip():
                continue
            chunks.append(
                CorpusChunk(
                    chunk_id=f"{path.stem}:{metadata.get('chunk_index', position)}",
                    content=content,
                    file_name=str(metadata.get("file_name") or ""),
                    page_start=metadata.get("page_start"),
                    page_end=metadata.get("page_end"),
                    section=metadata.get("section") or None,
                    chunk_index=int(metadata.get("chunk_index", position)),
                )
            )
    if not chunks:
        raise ValueError(f"Nenhum chunk encontrado em {processed_dir}")
    return chunks


def _first_document_rank(results: list[dict[str, Any]], expected: str | None) -> int | None:
    normalized_expected = _normalized_name(expected)
    return next(
        (
            rank
            for rank, result in enumerate(results, 1)
            if _normalized_name(result.get("file_name")) == normalized_expected
        ),
        None,
    )


def _page_hit(
    results: list[dict[str, Any]],
    expected_document: str | None,
    expected_pages: list[int],
    tolerance: int = 0,
) -> bool:
    acceptable = {
        page + offset
        for page in expected_pages
        for offset in range(-tolerance, tolerance + 1)
        if page + offset >= 1
    }
    normalized_expected = _normalized_name(expected_document)
    for result in results:
        if _normalized_name(result.get("file_name")) != normalized_expected:
            continue
        start = result.get("page_start")
        end = result.get("page_end") or start
        if isinstance(start, int) and isinstance(end, int):
            if set(range(start, end + 1)) & acceptable:
                return True
    return False


def summarize(records: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    answerable = [record for record in records if record["answerable"]]
    if not answerable:
        raise ValueError("Não há perguntas com resposta no acervo")
    return {
        "question_count": len(records),
        "answerable_count": len(answerable),
        "hit_rate_at_1": sum(record["first_relevant_rank"] == 1 for record in answerable)
        / len(answerable),
        f"hit_rate_at_{top_k}": sum(
            record["first_relevant_rank"] is not None for record in answerable
        )
        / len(answerable),
        "mrr": statistics.fmean(record["reciprocal_rank"] for record in answerable),
        "page_exact": sum(record["page_exact"] for record in answerable) / len(answerable),
        "page_tolerance_1": sum(record["page_tolerance_1"] for record in answerable)
        / len(answerable),
        "mean_retrieval_time_ms": statistics.fmean(
            record["retrieval_time_ms"] for record in answerable
        ),
    }


def _dense_summary(run: dict[str, Any], top_k: int) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for record in run["records"]:
        if not record["answerable"]:
            continue
        results = list(record.get("retrieval_results", []))[:top_k]
        rank = _first_document_rank(results, record.get("expected_document"))
        records.append(
            {
                "answerable": True,
                "first_relevant_rank": rank,
                "reciprocal_rank": 1 / rank if rank else 0.0,
                "page_exact": _page_hit(
                    results,
                    record.get("expected_document"),
                    record.get("expected_pages", []),
                ),
                "page_tolerance_1": _page_hit(
                    results,
                    record.get("expected_document"),
                    record.get("expected_pages", []),
                    1,
                ),
                "retrieval_time_ms": float(record.get("retrieval_time_ms") or 0),
            }
        )
    return summarize(records, top_k)


def evaluate_bm25(
    benchmark_path: Path,
    processed_dir: Path,
    *,
    top_k: int = 8,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    questions = [
        question
        for question in benchmark["questions"]
        if question.get("status") == "approved"
    ]
    chunks = load_chunks(processed_dir)
    index = BM25Index(chunks, k1=k1, b=b)
    records: list[dict[str, Any]] = []
    for question in questions:
        started = time.perf_counter()
        results = index.search(question["question"], top_k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        rank = (
            _first_document_rank(results, question.get("expected_document"))
            if question["answerable"]
            else None
        )
        records.append(
            {
                "id": question["id"],
                "split": question["split"],
                "question": question["question"],
                "answerable": question["answerable"],
                "expected_document": question.get("expected_document"),
                "expected_pages": question.get("expected_pages", []),
                "first_relevant_rank": rank,
                "reciprocal_rank": 1 / rank if rank else 0.0,
                "page_exact": bool(
                    question["answerable"]
                    and _page_hit(
                        results,
                        question.get("expected_document"),
                        question.get("expected_pages", []),
                    )
                ),
                "page_tolerance_1": bool(
                    question["answerable"]
                    and _page_hit(
                        results,
                        question.get("expected_document"),
                        question.get("expected_pages", []),
                        1,
                    )
                ),
                "retrieval_time_ms": elapsed_ms,
                "retrieval_results": results,
            }
        )
    summaries = {
        scope: summarize(
            records if scope == "overall" else [
                record for record in records if record["split"] == scope
            ],
            top_k,
        )
        for scope in ("overall", "development", "final")
    }
    return {
        "method": "BM25",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": benchmark.get("benchmark_version"),
        "parameters": {
            "top_k": top_k,
            "k1": k1,
            "b": b,
            "tokenization": "NFKC + casefold + palavras Unicode; sem stemming e sem stopwords",
            "retrieval_unit": "chunk",
        },
        "corpus": {
            "document_count": len({_normalized_name(chunk.file_name) for chunk in chunks}),
            "chunk_count": len(chunks),
        },
        "summaries": summaries,
        "records": records,
    }


def _comparison_rows(
    bm25: dict[str, Any],
    dense_runs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    top_k = int(bm25["parameters"]["top_k"])
    dense_by_split = {run["split"]: _dense_summary(run, top_k) for run in dense_runs}
    rows: list[dict[str, Any]] = []
    for split in ("development", "final"):
        for method, summary in (
            ("BM25", bm25["summaries"][split]),
            ("Denso", dense_by_split[split]),
        ):
            rows.append(
                {
                    "split": split,
                    "method": method,
                    "answerable_count": summary["answerable_count"],
                    "hit_rate_at_1": summary["hit_rate_at_1"],
                    f"hit_rate_at_{top_k}": summary[f"hit_rate_at_{top_k}"],
                    "mrr": summary["mrr"],
                    "page_exact": summary["page_exact"],
                    "page_tolerance_1": summary["page_tolerance_1"],
                    "mean_retrieval_time_ms": summary["mean_retrieval_time_ms"],
                }
            )
    return rows


def write_outputs(
    result: dict[str, Any],
    output_dir: Path,
    dense_run_paths: list[Path],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "bm25_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dense_runs = [read_json(path) for path in dense_run_paths]
    rows = _comparison_rows(result, dense_runs)
    csv_path = output_dir / "retrieval_comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    top_k = int(result["parameters"]["top_k"])
    table_rows = "\n".join(
        "| {split} | {method} | {hit1:.1%} | {hitk:.1%} | {mrr:.3f} | "
        "{page:.1%} | {page1:.1%} | {latency:.2f} |".format(
            split=row["split"],
            method=row["method"],
            hit1=row["hit_rate_at_1"],
            hitk=row[f"hit_rate_at_{top_k}"],
            mrr=row["mrr"],
            page=row["page_exact"],
            page1=row["page_tolerance_1"],
            latency=row["mean_retrieval_time_ms"],
        )
        for row in rows
    )
    report = f"""# Comparação do recuperador denso com o baseline BM25

O BM25 e o recuperador denso foram avaliados com as mesmas perguntas, os mesmos
chunks e `k={top_k}`. As métricas de recuperação usam somente as perguntas com
resposta no acervo. O BM25 usa `k1={result['parameters']['k1']}` e
`b={result['parameters']['b']}`, sem stemming e sem remoção de stopwords. O baseline
foi acrescentado retrospectivamente, depois da avaliação original, e seus parâmetros
convencionais não foram ajustados no conjunto final.

| Divisão | Método | Hit@1 | Hit@{top_k} | MRR | Página exata | Página ±1 | Latência média (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
{table_rows}

## Baseline da decisão de responder

Em cada divisão há 42 perguntas com resposta e 8 sem resposta. Um classificador que
sempre decidisse responder teria acurácia de 42/50 = 84%, recall de 100% para a classe
“com resposta” e especificidade de 0% para a classe “sem resposta”. Portanto, a
acurácia do sistema deve ser apresentada junto desse baseline; isoladamente, 84% não
demonstra ganho sobre a regra trivial de sempre responder.

## Limites

- O BM25 compara somente a recuperação; ele não gera respostas nem possui, por si só,
  uma regra de recusa comparável à do pipeline RAG.
- Como o baseline foi incorporado depois da avaliação original, a comparação deve ser
  descrita como retrospectiva, e não como hipótese confirmatória pré-registrada.
- O gabarito registra um único documento esperado por pergunta. Se outro TCC também
  contiver resposta válida, as métricas podem subestimar ambos os recuperadores.
- As oito perguntas negativas por divisão são insuficientes para sustentar uma
  estimativa precisa da taxa de falsos positivos.
"""
    (output_dir / "retrieval_comparison.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara a recuperação densa com um baseline lexical BM25"
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("evaluation/benchmark/benchmark_approved.json"),
    )
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--k1", type=float, default=1.5)
    parser.add_argument("--b", type=float, default=0.75)
    parser.add_argument(
        "--dense-run",
        type=Path,
        action="append",
        required=True,
        help="Informe uma vez para development e outra para final.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/results/bm25_baseline"),
    )
    args = parser.parse_args()
    if len(args.dense_run) != 2:
        parser.error("--dense-run deve ser informado duas vezes")
    result = evaluate_bm25(
        args.benchmark,
        args.processed_dir,
        top_k=args.top_k,
        k1=args.k1,
        b=args.b,
    )
    write_outputs(result, args.output_dir, args.dense_run)
    print(
        f"BM25 avaliado em {len(result['records'])} perguntas; "
        f"resultados em {args.output_dir}"
    )


if __name__ == "__main__":
    main()
