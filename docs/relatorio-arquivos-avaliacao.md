# Relatório de rastreabilidade dos arquivos usados na avaliação

## 1. Objetivo

Este relatório identifica os arquivos utilizados na avaliação experimental do
IFB Library Chat e explica a função de cada um. A finalidade é distinguir:

- os arquivos que definem o experimento;
- os arquivos efetivamente usados para executar as perguntas;
- os resultados históricos existentes e os futuros artefatos BM25 ponta a ponta;
- os relatórios derivados desses resultados;
- os experimentos preliminares de calibração;
- os testes automatizados de software, que não equivalem à avaliação das
  respostas do chatbot.

## 2. Visão geral do fluxo

```text
PDFs e chunks processados
        |
        v
full_corpus_draft.json / .xlsx
        |
        | revisão das perguntas e evidências
        v
benchmark_approved.json
        |
        +--------------------------+
        |                          |
        v                          v
split development             frozen_config.json
        |                          |
        | calibração               v
        |                     split final
        v                          |
development_run.json              v
                             final_run.json
        |                          |
        +------------+-------------+
                     |
                     v
             evaluation.complete
                     |
                     v
     resumo_metricas.csv, resultados_brutos.jsonl,
     resultados_detalhados.xlsx e relatório Markdown
```

O executor realiza duas chamadas por pergunta:

```text
POST /chat   -> resposta gerada e fontes utilizadas pelo RAG
POST /search -> oito resultados da busca vetorial registrados para as
                métricas de recuperação
```

Esse detalhe é importante: as métricas de Hit Rate e MRR são calculadas sobre
os resultados de `/search`, enquanto a resposta, a recusa e as fontes do
contexto são obtidas de `/chat`.

## 3. Fontes canônicas e estado dos experimentos

Os seguintes arquivos devem ser considerados as fontes principais para
documentar o experimento no TCC.

| Arquivo | Papel no experimento |
|---|---|
| `evaluation/benchmark/benchmark_approved.json` | Gabarito aprovado das 100 perguntas |
| `evaluation/config/frozen_config.json` | Barreira canônica ainda não congelada para a execução BM25 ponta a ponta |
| `evaluation/results/complete/development_run.json` | Execução densa histórica das 50 perguntas de desenvolvimento |
| `evaluation/results/complete/final_run.json` | Execução densa histórica das 50 perguntas do split final |
| `evaluation/results/complete/resultados_brutos.jsonl` | Consolidação auditável, uma pergunta por linha |
| `evaluation/results/complete/resumo_metricas.csv` | Métricas gerais, de desenvolvimento e finais |
| `evaluation/results/complete/experiment_manifest.json` | Hash do benchmark e metadados da consolidação |
| `evaluation/config/frozen_config_legacy_dense.json` | Configuração preservada da execução densa histórica |
| `evaluation/config/frozen_config_bm25.json` | Configuração da comparação BM25 retrospectiva |
| `evaluation/results/bm25_baseline/bm25_results.json` | Resultados BM25 por pergunta |
| `evaluation/results/bm25_baseline/retrieval_comparison.csv` | Comparação BM25 versus denso |
| `evaluation/RELATORIO_COMPLETO_REVISAO_METRICAS.md` | Texto final revisado para o TCC |

Os arquivos de `evaluation/results/complete` registram a execução histórica densa.
Eles são mantidos como evidência e não representam o recuperador BM25 integrado.

### 3.1 Gabarito aprovado

**Arquivo:** `evaluation/benchmark/benchmark_approved.json`

Esse arquivo contém 100 perguntas aprovadas:

- 50 de desenvolvimento;
- 50 de teste final;
- 42 perguntas com resposta no acervo e 8 sem resposta no acervo em cada split;
- 84 perguntas com resposta no acervo e 16 sem resposta no acervo no total.

Para cada pergunta com resposta no acervo são registrados:

- `id`;
- `question`;
- `answerable`;
- `question_type`;
- `difficulty`;
- `expected_answer`;
- `required_facts`;
- `expected_document`;
- `expected_pages`;
- `printed_pages`;
- `evidence`;
- `section`;
- `split`;
- `status`;
- `review_notes`.

O SHA-256 registrado para esse benchmark é:

```text
49440376b4b12c574d864e6162b63199e433e9bdcd06c469a507d70c7eb56486
```

O arquivo exclui justificadamente `Gabriela_Pinto_CEST.pdf` da avaliação de
respostas, pois o processamento encontrou conteúdo insuficiente para elaborar
duas perguntas verificáveis. Os outros 42 documentos possuem uma pergunta com
resposta no acervo em cada split.

### 3.2 Configuração congelada da execução histórica densa

**Arquivo preservado:** `evaluation/config/frozen_config_legacy_dense.json`

Esse arquivo registra a configuração selecionada antes da execução final:

| Parâmetro | Valor |
|---|---|
| `chunk_size` | 500 |
| `chunk_overlap` | 50 |
| `top_k` | 8 |
| `candidate_pool_size` | 24 |
| `similarity_threshold` | 0,35 |
| `duplicate_threshold` | 0,92 |
| `max_context_chars` | 12.000 |
| modelo de embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| modelo gerador | `gpt-4o-mini` |
| timeout do LLM | 60 segundos |
| benchmark | versão 2.0 |
| semente | 42 |

A configuração usada na comparação retrospectiva está registrada em
`evaluation/config/frozen_config_bm25.json`, com `retrieval_provider=bm25`,
`bm25_k1=1,5` e `bm25_b=0,75`. Ela não substitui o congelamento de uma execução
BM25 ponta a ponta.

Também são registrados o hash do prompt, a revisão Git conhecida no momento do
congelamento e a data UTC.

O caminho canônico `evaluation/config/frozen_config.json` permanece com
`status=not_frozen` até a análise do split de desenvolvimento atual. O executor novo
consulta `/health` e bloqueia a avaliação se configuração, prompt ou fingerprint do
corpus divergirem da API efetivamente em execução.

### 3.3 Execução histórica de desenvolvimento

**Arquivo:** `evaluation/results/complete/development_run.json`

Contém:

- 50 registros, IDs `Q001` a `Q050`;
- perguntas, gabaritos e respostas geradas;
- documentos e páginas recuperados;
- scores vetoriais;
- textos dos oito resultados de `/search`;
- fontes devolvidas por `/chat`;
- classificação de recusa;
- tempos;
- erros e timeouts;
- configuração registrada.

Essa execução começou em `2026-07-23T01:28:04Z` e terminou em
`2026-07-23T01:30:39Z`.

O desenvolvimento foi o conjunto usado para ajustes e calibração. Não existe
um terceiro split independente chamado `calibration`.

### 3.4 Execução histórica do split final

**Arquivo:** `evaluation/results/complete/final_run.json`

Contém os mesmos campos da execução de desenvolvimento, mas para os IDs `Q051`
a `Q100`.

A execução começou em `2026-07-23T01:30:49Z`, depois do congelamento, e terminou
em `2026-07-23T01:33:24Z`.

Esse é o arquivo primário para recalcular:

- TP, FP, FN e TN;
- precisão, recall, F1, FPR, FNR e acurácia;
- Hit Rate@1 e Hit Rate@8;
- MRR;
- recuperação de página;
- recusas corretas e indevidas;
- erros, timeouts e latências.

### 3.5 Resultados brutos consolidados

**Arquivo:** `evaluation/results/complete/resultados_brutos.jsonl`

Possui 100 linhas JSON, uma por pergunta. Cada linha combina:

- dados do benchmark;
- registro da execução;
- rank do documento esperado;
- Reciprocal Rank;
- hits de documento e página;
- presença de citações;
- decisão responder/recusar;
- indicação de necessidade de revisão manual.

É o arquivo mais conveniente para auditorias por pergunta. Ele não substitui os
dois arquivos de execução, pois foi produzido posteriormente por
`evaluation.complete`.

### 3.6 Resumo das métricas

**Arquivo:** `evaluation/results/complete/resumo_metricas.csv`

O CSV contém três escopos:

- `overall`: as 100 perguntas;
- `development`: as 50 perguntas de desenvolvimento;
- `final`: as 50 perguntas finais.

Para o resultado científico principal, devem ser usadas as linhas com
`scope=final`. As linhas `overall` misturam desenvolvimento, que participou da
calibração, com teste final.

### 3.7 Manifesto

**Arquivo:** `evaluation/results/complete/experiment_manifest.json`

Registra:

- data da consolidação;
- SHA-256 do benchmark;
- quantidade de perguntas;
- quantidade de perguntas com resposta e sem resposta no acervo;
- `top_k`;
- pool de candidatos;
- situação do juiz de qualidade.

O campo `judge_model` contém `não executado`. Portanto, correção factual,
fidelidade, completude e sustentação das citações não foram avaliadas pelo juiz
LLM.

## 4. Scripts usados na preparação e execução

### 4.1 `evaluation/generate_benchmark.py`

Gera os candidatos iniciais com base nos chunks processados. No modo
`--full-corpus`, cria duas perguntas candidatas por documento elegível e as
perguntas negativas.

Todos os candidatos são gerados como `pending_review`. Esse script não cria um
gabarito automaticamente aprovado.

### 4.2 `evaluation/review.py`

Importa uma planilha XLSX revisada e produz o JSON do benchmark. O script
preserva as decisões existentes na planilha e não aprova itens automaticamente.

### 4.3 `evaluation/validate_benchmark.py`

Verifica:

- total de perguntas;
- proporção de negativas;
- divisão 50/50;
- IDs duplicados;
- estado `approved`;
- existência dos PDFs;
- validade das páginas;
- cobertura dos 42 documentos avaliáveis;
- exclusão documental justificada;
- presença indevida de IDs finais em uma execução de desenvolvimento.

### 4.4 `evaluation/freeze_config.py`

Captura os parâmetros técnicos da aplicação e grava
`evaluation/config/frozen_config.json`.

### 4.5 `evaluation/run.py`

É o executor das perguntas. Para cada item:

1. chama `/chat`;
2. guarda resposta, fontes e tempos de geração;
3. chama `/search`;
4. guarda ranking, chunks, documentos, páginas e scores;
5. classifica a resposta como recusa ou não recusa;
6. grava um `RunRecord`.

O split final exige:

- `--confirm-final`;
- arquivo de configuração existente;
- `status=frozen`;
- mesma versão de benchmark.
- correspondência integral entre configuração, corpus e API publicada em
  `/health`.

### 4.6 `evaluation/metrics.py`

Implementa as métricas determinísticas do relatório simples:

- Document Recall/Hit Rate@1, @3 e @k;
- Page Recall@k;
- MRR;
- Recall e MRR separados para ranking inicial e contexto final;
- fonte do documento esperado;
- fonte da página esperada;
- recusa correta e indevida;
- matriz de confusão, acurácia, precisão, recall, F1 e baseline de sempre responder;
- respostas com fonte inline válida, sem fonte e recusas sem fonte inventada;
- latências;
- erros e timeouts.

### 4.7 `evaluation/report.py`

Transforma um arquivo de execução em:

- `report.json`;
- `report.csv`;
- `report.xlsx`;
- `report.html`.

Também cria campos editáveis para avaliação humana de correção, fidelidade,
completude e qualidade das citações.

### 4.8 `evaluation/import_scores.py`

Importa para o JSON as notas humanas preenchidas no relatório XLSX.

Não foi encontrado arquivo oficial `scored` com essas notas preenchidas.

### 4.9 `evaluation/complete.py`

Combina as execuções de desenvolvimento e final, calcula métricas adicionais e
gera os artefatos da pasta `evaluation/results/complete`.

O script também oferece um juiz LLM opcional. Na execução armazenada, esse juiz
não foi utilizado.

## 5. Arquivos da implementação RAG envolvidos

| Arquivo | Função durante o teste |
|---|---|
| `app/vectorstore/embeddings.py` | Carrega o modelo e normaliza embeddings |
| `app/vectorstore/service.py` | Executa a consulta HNSW/cosseno no Chroma |
| `app/retrieval/bm25.py` | Executa a recuperação lexical BM25 selecionada para o sistema final |
| `app/rag/service.py` | Recupera 24 candidatos, reranqueia, filtra e monta o contexto |
| `app/rag/prompts.py` | Define a obrigação de usar apenas o contexto e citar fontes |
| `app/rag/llm.py` | Envia prompts ao provedor de linguagem |
| `app/rag/factory.py` | Constrói recuperador, LLM e serviço RAG com a configuração |
| `app/routes/search.py` | Expõe o recuperador configurado usado nas métricas de recuperação |
| `app/routes/chat.py` | Expõe a resposta RAG usada nas métricas de recusa |
| `frontend/api_client.py` | Cliente usado pelo executor para chamar a API |

### 5.1 Recuperação oficial atual

`app/retrieval/bm25.py` constrói o índice lexical a partir dos mesmos artefatos de
chunks usados pela aplicação. A pontuação é BM25 de Okapi, com `k1=1,5` e
`b=0,75`, normalizada para o contrato público de relevância. O BM25 é o recuperador
padrão e é compartilhado pela API, CLI e comparação de recuperação.

A recuperação densa em `app/vectorstore/service.py` permanece implementada somente
para reprodução da execução histórica. Nessa configuração, o Chroma usa HNSW com
distância cosseno e converte a distância em `similarity = 1 - distance`.

### 5.2 Seleção do contexto

No pipeline oficial, `app/rag/service.py` solicita 24 candidatos ao BM25 e os ordena
pela tupla:

```python
(lexical_relevance, bm25_score_normalizado)
```

Não há combinação com embeddings no fluxo oficial, portanto ele não deve ser
descrito como híbrido. Trata-se de recuperação BM25 seguida por uma etapa heurística
de seleção de contexto.

### 5.3 Filtros e deduplicação

Um candidato é descartado quando:

```text
score BM25 normalizado < 0,35 E relevância lexical < 0,5
```

Chunks cujo conteúdo normalizado alcança razão de similaridade de 0,92 pelo
`SequenceMatcher` são tratados como duplicados.

## 6. Arquivos de preparação do benchmark

| Arquivo | Uso |
|---|---|
| `evaluation/benchmark/full_corpus_draft.json` | Rascunho automático com 100 candidatos |
| `evaluation/benchmark/full_corpus_draft.xlsx` | Planilha gerada para revisão |
| `evaluation/benchmark/corpus_100_questoes_corrigido.xlsx` | Planilha corrigida mantida como evidência da etapa de revisão |
| `evaluation/benchmark/benchmark_approved.json` | Resultado final aprovado e usado nas execuções oficiais |

Os arquivos `benchmark_draft.json`, `benchmark_draft.xlsx` e
`benchmark_approved.json` de versões anteriores devem ser identificados pela
versão interna do benchmark. Para a avaliação oficial de 100 perguntas, a fonte
canônica é `benchmark_approved.json` com `benchmark_version=2.0`.

## 7. Experimentos preliminares de desenvolvimento

Os arquivos abaixo registram etapas de calibração, mas não são o teste final:

| Etapa | Execução | Relatório |
|---|---|---|
| Linha de base | `evaluation/results/development_run.json` | `evaluation/results/development_baseline/` |
| Perguntas revisadas | `evaluation/results/development_run_questions_v1.json` | `evaluation/results/development_questions_v1/` |
| Reranqueamento v2 | `evaluation/results/development_run_rerank_v2.json` | `evaluation/results/development_rerank_v2/` |
| Comparação | — | `evaluation/results/development_comparison/` |

### Cuidados de interpretação

- A linha de base utilizou perguntas automáticas diferentes das perguntas
  revisadas.
- A melhora entre essas duas etapas não pode ser atribuída somente ao sistema.
- O reranqueamento v2 adicionou o pool de 24 candidatos e alterou o prompt.
- As métricas de recuperação de `/search` permaneceram iguais entre “perguntas
  revisadas” e “reranqueamento v2”, pois o endpoint `/search` não executa o
  reranqueamento do RAG.

Esses arquivos servem para documentar o processo de desenvolvimento, não para
substituir os números do split final.

## 8. Relatórios derivados

| Arquivo | Natureza |
|---|---|
| `evaluation/results/complete/relatorio_avaliacao.md` | Relatório Markdown gerado automaticamente |
| `evaluation/results/complete/tabela_resultados_latex.tex` | Tabela para inclusão no TCC |
| `evaluation/results/complete/resultados_detalhados.xlsx` | Planilha detalhada das 100 perguntas |
| `evaluation/results/complete/README_avaliacao.md` | Comandos de reprodução |

Esses arquivos são derivados. Se houver divergência, devem prevalecer:

1. `benchmark_approved.json`;
2. `development_run.json` e `final_run.json`;
3. código de cálculo das métricas.

## 9. Testes automatizados

Os arquivos em `tests/` verificam a implementação do software. Eles não foram
usados para calcular Hit Rate, MRR, F1 ou qualidade factual.

### 9.1 Avaliação e métricas

**Arquivo:** `tests/test_evaluation.py`

Verifica:

- geração e leitura do benchmark;
- distribuição dos splits;
- cobertura dos documentos;
- validação de páginas;
- detecção de vazamento de IDs;
- fórmulas de Recall e MRR;
- classificação textual de recusa;
- registro de erros e timeouts;
- exigência de confirmação e congelamento para o split final;
- geração dos relatórios.

### 9.2 Pipeline RAG

**Arquivo:** `tests/test_rag.py`

Verifica:

- uso do contexto;
- fontes retornadas;
- pool de candidatos;
- reranqueamento;
- limiar vetorial e regra lexical;
- deduplicação;
- ausência de chamada ao LLM quando não existe contexto;
- tratamento de falhas.

### 9.3 Vectorstore

**Arquivo:** `tests/test_vectorstore.py`

Verifica:

- persistência no Chroma;
- ausência de duplicação;
- substituição de versões antigas;
- busca densa e recuperação lexical BM25;
- metadados e similaridade;
- filtros;
- medição de tempo.

### 9.4 API e integração

**Arquivo:** `tests/test_api.py`

Verifica contratos HTTP, validação, limites, upload, busca, chat, erros e
documentação OpenAPI usando serviços simulados.

### 9.5 Frontend, ingestão e segurança

Os demais testes cobrem:

- cliente HTTP e apresentação das fontes;
- administração e upload;
- chunking;
- ingestão;
- metadados acadêmicos;
- segurança de documentos;
- configuração;
- saúde e observabilidade;
- integração com provedores de LLM.

Passar nesses testes significa que os componentes se comportam conforme as
regras implementadas. Não significa que o chatbot respondeu corretamente a uma
quantidade equivalente de perguntas.

## 10. Arquivos que não comprovam avaliação factual

Os seguintes campos existem no modelo, mas estão vazios nas execuções oficiais:

- `correctness`;
- `faithfulness`;
- `completeness`;
- `citation_quality`;
- `human_notes`;
- `llm_judge_score`.

Também não foi encontrado:

- arquivo oficial de execução com sufixo `scored`;
- checkpoint bem-sucedido do juiz LLM;
- notas de dois avaliadores;
- cálculo de concordância;
- rotulagem de relevância de cada chunk.

Consequentemente, os arquivos existentes não sustentam afirmações quantitativas
sobre:

- correção factual;
- fidelidade;
- completude;
- alucinação;
- precisão dos chunks;
- recall dos chunks;
- F1 de recuperação.

## 11. Divergência nas métricas de citação

O relatório completo apresenta `citation_document_correct=0` e
`citation_page_exact=0`. Esses valores não significam ausência de fontes
corretas.

Essas duas métricas dependem do campo `citation_support` produzido pelo juiz
LLM. Como o juiz não foi executado, o campo ficou ausente, mas
`evaluation.complete` converteu a condição em `False` e a contabilizou como
mensurável.

Diretamente no `final_run.json` **da execução densa histórica**, é possível
verificar:

- documento esperado entre as fontes do `/chat`: 37/42;
- documento e página esperados entre as fontes: 28/42;
- resposta com referência inline `[Fonte N]`: 34/42.

Para o TCC, os `0%` do relatório completo devem ser descritos como não
mensuráveis, não como zero acertos.

## 12. Quais arquivos usar em cada seção do TCC

| Seção do TCC | Arquivos recomendados |
|---|---|
| Construção do benchmark | `generate_benchmark.py`, `full_corpus_draft.xlsx`, `benchmark_approved.json` |
| Protocolo e divisão | `PROTOCOL.md`, `validate_benchmark.py`, `benchmark_approved.json` |
| Configuração atual | `frozen_config.json`, `runtime.py`, `configuration.py`, `app/config.py` |
| Recuperação atual | `retrieval/bm25.py`, `retrieval/factory.py`, `rag/service.py` |
| Execução BM25 ponta a ponta | `evaluation/run.py`, futura pasta `results/official_bm25/` |
| Execução densa histórica | `results/complete/development_run.json`, `results/complete/final_run.json` |
| Fórmulas | `evaluation/metrics.py`, `evaluation/complete.py` |
| Comparação retrospectiva | `results/bm25_baseline/bm25_results.json`, `retrieval_comparison.csv` |
| Resultados BM25 ponta a ponta | ainda não produzidos; não substituir por resultados densos |
| Limitações | `experiment_manifest.json`, campos humanos vazios e divergências descritas neste relatório |
| Testes de software | arquivos em `tests/`, separados da avaliação experimental |

## 13. Sequência mínima para reprodução

```bash
python -m evaluation.validate_benchmark \
  --benchmark evaluation/benchmark/benchmark_approved.json

python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split development \
  --output evaluation/results/official_bm25/development_run.json

# Somente depois de analisar o desenvolvimento e encerrar os ajustes:
python -m evaluation.freeze_config

# Usar apenas com um split final ainda não observado e confirmação deliberada:
python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split final \
  --confirm-final \
  --output evaluation/results/official_bm25/final_run.json

python -m evaluation.complete \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --development-run evaluation/results/official_bm25/development_run.json \
  --final-run evaluation/results/official_bm25/final_run.json \
  --output-dir evaluation/results/official_bm25/complete \
  --skip-llm-judge
```

Antes de uma nova reprodução, deve-se garantir que:

- a API está executando a mesma revisão do código;
- a API usa exatamente os parâmetros congelados;
- o índice Chroma e os chunks não foram alterados;
- o hash do benchmark continua igual;
- nenhuma pergunta final foi usada para novos ajustes.

## 14. Síntese

A futura avaliação BM25 ponta a ponta será definida por quatro arquivos principais:

```text
benchmark_approved.json
frozen_config.json
development_run.json
final_run.json
```

Neste repositório, apenas o benchmark existe nesse conjunto novo; a configuração
canônica está deliberadamente `not_frozen` e os dois arquivos de execução ainda não
foram produzidos. Os scripts de avaliação transformam esses arquivos em métricas e relatórios. Os
arquivos das pastas `development_baseline`, `development_questions_v1` e
`development_rerank_v2` documentam calibração preliminar. Os arquivos em
`tests/` verificam o software, mas não medem a qualidade das respostas.

Os resultados em `results/complete` podem ser apresentados somente como execução
densa histórica. Os resultados em `results/bm25_baseline` podem ser apresentados
somente como comparação retrospectiva de recuperação. Nenhum deles deve ser
renomeado ou reinterpretado como avaliação BM25 ponta a ponta.
