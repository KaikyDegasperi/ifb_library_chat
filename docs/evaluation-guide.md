# Guia de avaliação

## 1. Instalação

```bash
uv sync --locked
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

Os PDFs devem ter sido ingeridos pelo Docling. Para reproduzir o benchmark oficial de
100 perguntas, use o modo de corpus completo:

```bash
uv run python -m evaluation.generate_benchmark --full-corpus --seed 42
```

O comando cria `full_corpus_draft.json` e `full_corpus_draft.xlsx`. Todos os itens
começam como `pending_review`; respostas e evidências são propostas, não gabaritos
validados.

## 4. Revisão humana e aprovação

Abra `evaluation/benchmark/full_corpus_draft.xlsx`. Para cada linha, confira o PDF pelo
caminho da última coluna e as páginas reais indicadas, edite pergunta, resposta e
fatos, e defina `status` como `approved`, `rejected` ou `pending_review`. Perguntas com
resposta no acervo só podem ser aprovadas com documento, página e evidência
verificáveis.

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

O benchmark oficial válido possui 100 itens aprovados: em cada divisão são 42
perguntas com resposta no acervo e oito sem resposta no acervo. Itens rejeitados devem
ser corrigidos ou substituídos e revisados novamente.

## 5. Desenvolvimento

Use somente o split de desenvolvimento para escolher parâmetros:

```bash
uv run python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split development \
  --output evaluation/results/official_bm25/development_run.json
```

Antes da primeira pergunta, o executor consulta `/health` e compara recuperador,
parâmetros BM25, `top_k`, chunking, limiares, modelo gerador e hash do prompt com a
configuração registrada. A execução é interrompida se a API ativa divergir.

Para auditar que nenhum item final vazou para uma execução de desenvolvimento:

```bash
uv run python -m evaluation.validate_benchmark \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --development-run evaluation/results/official_bm25/development_run.json
```

## 6. Congelamento

Depois de concluir todos os ajustes usando apenas desenvolvimento:

```bash
uv run python -m evaluation.freeze_config \
  --benchmark evaluation/benchmark/benchmark_approved.json
```

O arquivo canônico `evaluation/config/frozen_config.json` tem `status: not_frozen` e
serve como barreira explícita. O comando o substitui por uma captura completa com
`status: frozen`. Revise e versione o arquivo gerado. Não altere configurações após
observar resultados finais. A configuração da execução densa foi preservada em
`evaluation/config/frozen_config_legacy_dense.json`; a configuração da comparação
BM25 retrospectiva permanece em `evaluation/config/frozen_config_bm25.json`.

## 7. Execução final

O comando exige as duas barreiras: arquivo congelado e confirmação explícita.

```bash
uv run python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split final \
  --confirm-final \
  --output evaluation/results/official_bm25/final_run.json
```

Esse comando não deve ser executado durante desenvolvimento. A entrega do módulo não executa o split final.
Os arquivos em `evaluation/results/complete` são da execução densa histórica;
não os sobrescreva nem os atribua ao pipeline BM25 atual. Como o conjunto final
existente já foi observado na comparação retrospectiva, uma confirmação rigorosa
requer um conjunto novo e ainda não observado.

## 8. Relatórios e notas humanas

Gere os quatro formatos:

```bash
uv run python -m evaluation.report \
  --run evaluation/results/official_bm25/development_run.json \
  --output-dir evaluation/results/official_bm25/development
```

No `report.xlsx`, preencha as colunas amarelas `correctness`, `faithfulness`, `completeness`, `citation_quality` (0, 1 ou 2) e `human_notes`. A rubrica é: 0 incorreto/inventado; 1 parcial; 2 correto e sustentado.

Importe as notas e gere novamente os relatórios:

```bash
uv run python -m evaluation.import_scores \
  --run evaluation/results/official_bm25/development_run.json \
  --xlsx evaluation/results/official_bm25/development/report.xlsx \
  --output evaluation/results/official_bm25/development_run_scored.json

uv run python -m evaluation.report \
  --run evaluation/results/official_bm25/development_run_scored.json \
  --output-dir evaluation/results/official_bm25/development_scored
```

## 9. Interpretação

- Recall de documento e MRR do estágio inicial usam o ranking de `/search`.
- Recall e MRR de contexto usam `retrieved_context`, separado das fontes públicas.
- Recall de página exige interseção entre páginas esperadas e recuperadas.
- Taxas de citação usam `sources`, as fontes efetivamente citadas e apresentadas.
- A matriz de confusão e as contagens absolutas acompanham acurácia, precisão,
  recall, F1 e o baseline de sempre responder.
- Recusa correta exige pergunta marcada como sem resposta no acervo e resposta explicitamente negativa.
- Recusa indevida é uma negativa em pergunta com resposta no acervo.
- Resposta indevida é uma resposta não negativa a uma pergunta sem resposta.

O score vetorial nunca é tratado como prova de correção. Resultados sem nota humana continuam sem nota; nenhuma avaliação automática substitui a revisão.
Uma execução completa também depende do provedor de LLM configurado e de sua
credencial, que nunca é gravada nos artefatos.
