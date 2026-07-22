"""Congela a configuração escolhida exclusivamente com o split development."""

import argparse
from pathlib import Path

from app.config import get_settings
from evaluation.configuration import frozen_configuration
from evaluation.io import read_benchmark, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Congela configuração para a avaliação final")
    parser.add_argument("--benchmark", type=Path, default=Path("evaluation/benchmark/benchmark_approved.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/config/frozen_config.json"))
    args = parser.parse_args()
    benchmark = read_benchmark(args.benchmark)
    write_json(args.output, frozen_configuration(get_settings(), benchmark.benchmark_version, benchmark.seed))
    print(f"Configuração congelada em {args.output}. Não ajuste parâmetros usando o split final.")


if __name__ == "__main__":
    main()
