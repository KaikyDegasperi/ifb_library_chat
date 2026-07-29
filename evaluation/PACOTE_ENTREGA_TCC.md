# Pacote final da avaliação para o TCC

## Arquivos que devem ser usados

1. `evaluation/RELATORIO_COMPLETO_REVISAO_METRICAS.md`: texto principal do capítulo,
   incluindo método, comparação, métricas, limitações, síntese e conclusão.
2. `evaluation/TABELAS_FINAIS_TCC.tex`: tabelas revisadas prontas para o documento.
3. `evaluation/results/bm25_baseline/retrieval_comparison.csv`: valores tabulares
   auditáveis da comparação.
4. `evaluation/results/bm25_baseline/bm25_results.json`: resultados por pergunta do
   baseline lexical.
5. `evaluation/config/frozen_config_bm25.json`: configuração BM25 registrada.

## Artefatos históricos que devem ser preservados

O diretório `evaluation/results/complete` registra a execução original com recuperação
densa. Seus JSON, JSONL, CSV e XLSX são evidências históricas e não devem ser
reescritos. O relatório e a tabela desse diretório foram rotulados como históricos
para impedir que sejam confundidos com a versão final BM25.

## Afirmações permitidas

- O BM25 foi selecionado no conjunto de desenvolvimento e integrado como recuperador
  principal.
- Na recuperação final, o BM25 obteve Hit@1 de 97,62%, Hit@8 de 100% e MRR de 0,988.
- O recuperador denso obteve Hit@1 de 64,29%, Hit@8 de 83,33% e MRR de 0,713 no mesmo
  conjunto.
- Na execução histórica da decisão, o recall foi de 80,95%.
- Não houve falso positivo nas oito perguntas sem resposta do conjunto final.
- A acurácia de 84% foi igual à do baseline de responder sempre.
- A correção factual das respostas não foi medida.

## Afirmações que não devem aparecer

- “O sistema possui precisão perfeita.”
- “A precisão real é 100%.”
- “A qualidade das respostas foi comprovada.”
- “O BM25 obteve recall de decisão de 80,95%.”
- “A acurácia de 84% demonstra superioridade.”
- “A F1 verdadeira está necessariamente entre 81% e 89%.”

Os 80,95% de recall da decisão pertencem à execução histórica densa. O BM25 reproduziu
e superou os resultados de recuperação, mas a métrica de decisão depende também do
gerador externo e não deve ser transferida entre configurações.

## Terminologia obrigatória

Usar:

- “perguntas com resposta no acervo”;
- “perguntas sem resposta no acervo”;
- “recuperador BM25” ou “recuperação lexical”;
- “recuperador denso” para a configuração histórica comparada.

Evitar:

- “respondíveis”;
- “não respondíveis”;
- “precisão de 100%” sem a ressalva do tamanho da amostra.

## Checklist antes da entrega

- [ ] Transferir o relatório consolidado para o arquivo Word, LaTeX ou Overleaf do TCC.
- [ ] Inserir as três tabelas finais.
- [ ] Remover F0,5 da síntese e manter apenas F1 com a limitação.
- [ ] Conferir resumo, capítulo de avaliação e conclusão para evitar precisão perfeita.
- [ ] Relacionar toda menção à acurácia de 84% ao baseline de responder sempre.
- [ ] Declarar desde o início que a qualidade factual das respostas não foi medida.
- [ ] Declarar que o gabarito usa um único documento esperado por pergunta.
- [ ] Identificar as métricas de decisão como execução histórica densa.
- [ ] Apresentar o BM25 como recuperador final implementado.
