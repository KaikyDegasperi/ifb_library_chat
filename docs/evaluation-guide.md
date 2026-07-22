# Guia de avaliação

## 1. Instalação

```bash
uv sync
```

Inicie a API em outro terminal antes de executar perguntas:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 2. Diagnóstico do acervo

O caminho padrão vem de `DOCUMENTS_DIR`. Também pode ser informado explicitamente:

```bash
uv run python -m evaluation.diagnose --input ./pdfs_ifb
```

São criados `corpus_diagnostics.json`, `.csv` e `.html` em `evaluation/results`. O HTML funciona offline e filtra por status.

## 3. Geração assistida

Os PDFs devem ter sido ingeridos pelo Docling. Gere os 50 candidatos de forma reproduzível:

```bash
uv run python -m evaluation.generate_benchmark --questions 50 --unanswerable-ratio 0.20 --seed 42
```

O comando cria `benchmark_draft.json` e `benchmark_draft.xlsx`. Todos os itens começam como `pending_review`; respostas e evidências são propostas, não gabaritos validados.

## 4. Revisão humana e aprovação

Abra `evaluation/benchmark/benchmark_draft.xlsx`. Para cada linha, confira o PDF pelo caminho da última coluna e as páginas reais indicadas, edite pergunta, resposta e fatos, e defina `status` como `approved`, `rejected` ou `pending_review`. Perguntas respondíveis só podem ser aprovadas com documento, página e evidência verificáveis.

Depois salve uma cópia e importe-a:

```bash
uv run python -m evaluation.review \
  --xlsx evaluation/benchmark/benchmark_reviewed.xlsx \
  --output evaluation/benchmark/benchmark_approved.json
```

Valide:

```bash
uv run python -m evaluation.validate_benchmark \
  --benchmark evaluation/benchmark/benchmark_approved.json
```

Um benchmark válido precisa ter 50 itens aprovados, 40 respondíveis, 10 sem resposta e splits 25/25. Itens rejeitados devem ser corrigidos ou substituídos e revisados novamente.

## 5. Desenvolvimento

Use somente o split de desenvolvimento para escolher parâmetros:

```bash
uv run python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split development \
  --output evaluation/results/development_run.json
```

Para auditar que nenhum item final vazou para uma execução de desenvolvimento:

```bash
uv run python -m evaluation.validate_benchmark \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --development-run evaluation/results/development_run.json
```

## 6. Congelamento

Depois de concluir todos os ajustes usando apenas desenvolvimento:

```bash
uv run python -m evaluation.freeze_config \
  --benchmark evaluation/benchmark/benchmark_approved.json
```

O arquivo entregue inicialmente tem `status: not_frozen` e serve como barreira explícita. O comando o substitui por uma captura com `status: frozen`. Revise e versione `evaluation/config/frozen_config.json`. Não altere configurações após observar resultados finais.

## 7. Execução final

O comando exige as duas barreiras: arquivo congelado e confirmação explícita.

```bash
uv run python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split final \
  --confirm-final \
  --output evaluation/results/final_run.json
```

Esse comando não deve ser executado durante desenvolvimento. A entrega do módulo não executa o split final.

## 8. Relatórios e notas humanas

Gere os quatro formatos:

```bash
uv run python -m evaluation.report \
  --run evaluation/results/development_run.json \
  --output-dir evaluation/results
```

No `report.xlsx`, preencha as colunas amarelas `correctness`, `faithfulness`, `completeness`, `citation_quality` (0, 1 ou 2) e `human_notes`. A rubrica é: 0 incorreto/inventado; 1 parcial; 2 correto e sustentado.

Importe as notas e gere novamente os relatórios:

```bash
uv run python -m evaluation.import_scores \
  --run evaluation/results/development_run.json \
  --xlsx evaluation/results/report.xlsx \
  --output evaluation/results/development_run_scored.json

uv run python -m evaluation.report \
  --run evaluation/results/development_run_scored.json \
  --output-dir evaluation/results
```

## 9. Interpretação

- Recall de documento verifica se o arquivo esperado aparece até a posição indicada.
- Recall de página exige interseção entre páginas esperadas e recuperadas.
- MRR premia o primeiro documento correto em posições mais altas.
- Taxas de citação usam as fontes efetivamente apresentadas por `/chat`.
- Recusa correta exige pergunta marcada como não respondível e resposta explicitamente negativa.
- Recusa indevida é uma negativa em pergunta respondível.
- Resposta indevida é uma resposta não negativa a uma pergunta sem resposta.

O score vetorial nunca é tratado como prova de correção. Resultados sem nota humana continuam sem nota; nenhuma avaliação automática substitui a revisão.
