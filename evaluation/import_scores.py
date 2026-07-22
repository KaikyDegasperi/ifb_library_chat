"""Importa notas humanas editadas no report.xlsx para o JSON da execução."""

import argparse
from pathlib import Path

from openpyxl import load_workbook

from evaluation.io import read_json, write_json
from evaluation.models import HumanScores, RunOutput


SCORE_FIELDS = ("correctness", "faithfulness", "completeness", "citation_quality", "human_notes")


def import_scores(run_path: Path, xlsx_path: Path, output_path: Path) -> RunOutput:
    run = RunOutput.model_validate(read_json(run_path))
    sheet = load_workbook(xlsx_path, data_only=True)["details"]
    headers = [str(cell.value) for cell in sheet[1]]
    scores: dict[str, HumanScores] = {}
    for values in sheet.iter_rows(min_row=2, values_only=True):
        row = dict(zip(headers, values, strict=False))
        if row.get("id"):
            payload = {field: row.get(field) for field in SCORE_FIELDS}
            payload["human_notes"] = payload.get("human_notes") or ""
            scores[str(row["id"])] = HumanScores.model_validate(payload)
    for record in run.records:
        if record.id in scores:
            for field, value in scores[record.id].model_dump().items():
                setattr(record, field, value)
    write_json(output_path, run.model_dump(mode="json"))
    return run


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa notas humanas do XLSX")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--xlsx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = import_scores(args.run, args.xlsx, args.output)
    print(f"Notas importadas para {len(result.records)} registros em {args.output}")


if __name__ == "__main__":
    main()
