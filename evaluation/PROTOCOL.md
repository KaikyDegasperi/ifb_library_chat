# Protocolo de avaliação do IFB Library Chat

## Objetivo

Avaliar separadamente se o sistema recupera evidências corretas dos 43 TCCs e se
produz respostas corretas, completas, fiéis às fontes e com citações adequadas. A
avaliação também verifica recusas quando a informação não pertence ao acervo e
registra o tempo de resposta.

## Corpus e unidade de análise

- Corpus fechado: 43 TCCs da Licenciatura em Matemática do IFB Campus Estrutural.
- Unidade de recuperação: trecho indexado, com nome do PDF e intervalo de páginas.
- Pré-condição: os 43 PDFs devem possuir artefatos Docling e chunks indexados.
- O diagnóstico do corpus deve ser anexado, incluindo PDFs com pouco texto, páginas
  vazias e necessidade provável de OCR.

## Benchmark 2.0

O diagnóstico identificou um PDF sem conteúdo suficiente após extração/OCR. Ele
permanece contabilizado no corpus, mas é excluído da avaliação de respostas com motivo
registrado. O benchmark contém 100 perguntas:

- desenvolvimento: 42 perguntas respondíveis (uma por TCC avaliável) e 8 sem resposta;
- teste final: 42 perguntas respondíveis (uma nova por TCC avaliável) e 8 sem resposta;
- total: 84 perguntas respondíveis e 16 sem resposta no acervo.

Cada pergunta respondível registra resposta esperada, fatos obrigatórios, PDF,
página(s), trecho de evidência, seção, tipo e dificuldade. Os candidatos gerados
automaticamente permanecem `pending_review`. Um revisor deve abrir o PDF, conferir a
evidência e a numeração real das páginas, editar a pergunta e somente então marcar
`approved`. Perguntas finais não podem ser usadas para ajustar o sistema.

## Métricas

### Recuperação

- Document Recall@1, @3 e @k: proporção em que o TCC correto aparece nos primeiros
  resultados.
- Page Recall@k: proporção em que ao menos uma página esperada foi recuperada.
- MRR: valor médio do inverso da posição do primeiro documento correto.

### Geração (avaliação humana cega, escala 0–2)

- correção: compatibilidade com a resposta e os fatos esperados;
- fidelidade: toda afirmação está sustentada pelos trechos recuperados;
- completude: contempla os fatos obrigatórios relevantes;
- qualidade da citação: identifica corretamente documento e página.

Recomenda-se dois avaliadores em uma amostra de pelo menos 20 respostas e o relato da
concordância (Cohen's kappa ponderado ou concordância percentual). Divergências devem
ser resolvidas por consenso, sem alterar as perguntas finais.

### Segurança e operação

- taxa de recusa correta nas 16 perguntas sem resposta;
- taxa de recusa indevida nas 84 perguntas respondíveis;
- média, mediana e percentil 95 da latência;
- quantidade de erros e timeouts.

## Procedimento reproduzível

1. Diagnosticar os 43 PDFs e corrigir documentos não processados.
2. Gerar `full_corpus_draft.json` e `full_corpus_draft.xlsx`.
3. Revisar manualmente o XLSX usando os links para os PDFs.
4. Importar o XLSX revisado como `benchmark_approved.json` e validar.
5. Executar somente o split `development`; ajustar configurações apenas com ele.
6. Congelar código, prompt, modelo, chunking, limiar e `top_k`.
7. Executar o split `final` uma única vez com confirmação explícita.
8. Avaliar as respostas no XLSX, importar as notas e gerar JSON, CSV, XLSX e HTML.
9. Relatar todas as métricas, inclusive falhas, sem selecionar apenas casos favoráveis.

## Comandos

```bash
python -m evaluation.diagnose
python -m evaluation.generate_benchmark --full-corpus
python -m evaluation.review --xlsx evaluation/benchmark/full_corpus_draft.xlsx
python -m evaluation.validate_benchmark --benchmark evaluation/benchmark/benchmark_approved.json
python -m evaluation.run --benchmark evaluation/benchmark/benchmark_approved.json --split development --output evaluation/results/development_run.json
python -m evaluation.freeze_config
python -m evaluation.run --benchmark evaluation/benchmark/benchmark_approved.json --split final --confirm-final --output evaluation/results/final_run.json
python -m evaluation.report --run evaluation/results/final_run.json --output-dir evaluation/results/final
```

## Interpretação

Os resultados demonstram desempenho apenas sobre este corpus fechado e sobre as
perguntas aprovadas. Eles não provam correção universal do modelo nem substituem um
estudo de usabilidade com participantes. Essa delimitação deve permanecer explícita
na metodologia, nos resultados e na conclusão do TCC.
