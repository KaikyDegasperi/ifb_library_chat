# Reprodução da avaliação

> Este diretório preserva a execução histórica com recuperação densa. Ele não
> representa o BM25 atualmente integrado. Os arquivos JSON e CSV brutos não devem ser
> editados, pois são evidências da execução original.

Pré-requisitos: API ativa em `127.0.0.1:8000`, 43 PDFs processados, Chroma carregado e provedor LLM configurado.

Benchmark congelado: `49440376b4b12c574d864e6162b63199e433e9bdcd06c469a507d70c7eb56486`.

```bash
python -m evaluation.validate_benchmark --benchmark evaluation/benchmark/benchmark_approved.json
python -m evaluation.freeze_config
python -m evaluation.run --benchmark evaluation/benchmark/benchmark_approved.json --split development --output evaluation/results/complete/development_run.json
python -m evaluation.run --benchmark evaluation/benchmark/benchmark_approved.json --split final --confirm-final --output evaluation/results/complete/final_run.json
python -m evaluation.complete --benchmark evaluation/benchmark/benchmark_approved.json --development-run evaluation/results/complete/development_run.json --final-run evaluation/results/complete/final_run.json --output-dir evaluation/results/complete
```

O avaliador grava checkpoint do juiz em `judge_checkpoint.jsonl`. Remova esse arquivo somente se desejar pagar e executar novamente todas as avaliações do juiz. Para três repetições, execute cada split três vezes com nomes distintos e agregue por ID; esta execução oficial utilizou uma repetição.
