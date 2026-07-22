"""Importa a planilha revisada para JSON sem aprovar itens automaticamente."""

import argparse
from pathlib import Path

from evaluation.io import benchmark_from_xlsx, write_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa decisões humanas da planilha")
    parser.add_argument("--xlsx", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evaluation/benchmark/benchmark_approved.json"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    benchmark = benchmark_from_xlsx(args.xlsx, args.seed)
    write_benchmark(args.output, benchmark)
    counts = {status: sum(q.status == status for q in benchmark.questions) for status in ("approved", "rejected", "pending_review")}
    print(f"Importação concluída: {counts}")


if __name__ == "__main__":
    main()
