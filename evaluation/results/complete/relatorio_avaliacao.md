# Relatório histórico da configuração com recuperação densa

> **Atenção:** este artefato registra a execução original com recuperação densa.
> Ele foi preservado para rastreabilidade e não representa o recuperador BM25
> atualmente integrado. Para o texto final do TCC, use
> `evaluation/RELATORIO_COMPLETO_REVISAO_METRICAS.md`.

## Metodologia

- Benchmark congelado: `49440376b4b12c574d864e6162b63199e433e9bdcd06c469a507d70c7eb56486`.
- Amostra: 100 perguntas (84 com resposta no acervo e 16 sem resposta no acervo).
- Execuções por pergunta: 1. Estabilidade entre repetições: não mensurável nesta execução principal.
- Recuperação reportada: k=8; pool interno de candidatos=24.
- Página utilizada: página física do PDF (`page_start/page_end` do Chroma). A página impressa foi preservada separadamente quando disponível.
- Juiz de qualidade: `não executado`, temperatura 0, prompt versionado 1.0.
- O conjunto foi tratado como fixo durante esta execução; nenhum campo do gabarito foi modificado.

## Fórmulas

- Hit Rate@k = perguntas com o documento esperado entre as k primeiras / perguntas com resposta no acervo.
- RR = 1/posição do primeiro documento esperado; MRR = média dos RR.
- Completude = fatos obrigatórios corretamente mencionados / fatos obrigatórios.
- Resposta plenamente correta exige correção factual, completude 1, fidelidade 1, relevância 1, sustentação da citação 1 e ausência de recusa.

## Resultados gerais

| Métrica | Resultado | Observação |
|---|---:|---|
| hit_rate_at_1 | 70.2% (59/84) |  |
| hit_rate_at_8 | 88.1% (74/84) |  |
| mrr | 0.7655 (N=84) |  |
| page_exact | 60.7% (51/84) |  |
| page_tolerance_1 | 65.5% (55/84) |  |
| citation_document_correct | não mensurável | O juiz de qualidade não foi executado. |
| citation_page_exact | não mensurável | O juiz de qualidade não foi executado. |
| factual_correct | não mensurável |  |
| mean_completeness | não mensurável |  |
| mean_faithfulness | não mensurável |  |
| mean_relevance | não mensurável |  |
| fully_correct | não mensurável | A correção factual das respostas não foi avaliada. |
| correct_refusal | 100.0% (16/16) | Não houve falso positivo nas 16 perguntas negativas somadas; no conjunto final foram apenas 8 casos. |
| improper_refusal | 9.5% (8/84) |  |
| improper_answer | 0.0% (0/16) |  |
| latency_total_ms_mean | 3103.1800 (N=100) |  |
| latency_total_ms_p95 | 5078.0000 (N=100) |  |
| latency_total_ms_p99 | 7169.0000 (N=100) |  |
| errors | 0.0% (0/100) |  |
| timeouts | 0.0% (0/100) |  |
| manual_review_required | 84.0% (84/100) |  |

## Validação e limitações

- IDs duplicados: nenhum.
- Perguntas ignoradas: nenhuma.
- Erros e timeouts permanecem no denominador operacional e são apresentados explicitamente.
- Avaliação factual e evidência suficiente usam juiz LLM e não substituem validação humana.
- Como o juiz não foi executado, correção factual, fidelidade, completude, sustentação
  das citações e resposta plenamente correta são dimensões não mensuradas; valores
  nulos do artefato bruto não devem ser interpretados como desempenho igual a zero.
- A ausência de falso positivo no conjunto final ocorreu em somente oito perguntas
  sem resposta no acervo e não demonstra precisão perfeita em uso real.
- A acurácia final de 84% é igual à do baseline trivial de responder sempre e não deve
  ser apresentada isoladamente.
- O gabarito registra um único documento esperado por pergunta; documentos
  alternativos válidos podem fazer a recuperação ser subestimada.
- Foram marcadas 84 respostas para revisão manual, incluindo todos os casos reprovados/ambíguos e uma amostra sistemática de 20% dos demais.
- A comparação com execuções anteriores não é válida neste relatório porque elas não utilizaram exatamente o mesmo texto das 100 perguntas.
- Uma execução por pergunta é o resultado principal; três repetições ficaram fora do escopo por custo e tempo, logo estabilidade não é mensurável aqui.
