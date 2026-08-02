"""Congela a configuração escolhida exclusivamente com o split development."""

import argparse
from pathlib import Path

from app.config import Settings, get_settings
from evaluation.configuration import benchmark_fingerprint, frozen_configuration
from evaluation.io import read_benchmark, write_json


def freeze_configuration(
    settings: Settings,
    benchmark_path: Path,
    output_path: Path,
) -> dict:
    """Grava uma captura sem incluir perguntas ou gabaritos do benchmark."""
    benchmark = read_benchmark(benchmark_path)
    frozen = frozen_configuration(
        settings,
        benchmark.benchmark_version,
        benchmark.seed,
        benchmark_fingerprint(benchmark_path),
    )
    write_json(output_path, frozen)
    return frozen


def main() -> None:
    parser = argparse.ArgumentParser(description="Congela configuração para a avaliação final")
    parser.add_argument("--benchmark", type=Path, default=Path("evaluation/benchmark/benchmark_approved.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/config/frozen_config.json"))
    args = parser.parse_args()
    freeze_configuration(get_settings(), args.benchmark, args.output)
    print(f"Configuração congelada em {args.output}. Não ajuste parâmetros usando o split final.")


if __name__ == "__main__":
    main()
