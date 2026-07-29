# Texto sugerido para o TCC

## Escopo da avaliação

A avaliação cobre duas dimensões do sistema: a decisão de responder ou recusar uma
pergunta e a recuperação dos documentos e páginas usados como contexto. A correção
factual, a fidelidade e a completude das respostas geradas não foram medidas nesta
etapa. Portanto, os resultados não devem ser interpretados como uma avaliação da
qualidade textual ou factual das respostas finais.

> Esta é uma versão resumida. Para o capítulo completo, use
> `evaluation/RELATORIO_COMPLETO_REVISAO_METRICAS.md`.

## Comparação e seleção do recuperador

Para dar uma referência aos resultados do recuperador denso, foi implementado um
baseline lexical BM25. Os dois métodos receberam as mesmas perguntas e operaram sobre
os mesmos chunks produzidos na ingestão, com `k=8`. Assim, a única variável alterada
foi o método de ranqueamento. O BM25 utilizou os parâmetros convencionais `k1=1,5` e
`b=0,75`, definidos sem ajuste no conjunto final, e tokenização Unicode sem stemming
ou remoção de stopwords. Como o baseline foi incorporado depois da avaliação
original, a comparação tem caráter retrospectivo e não corresponde a uma hipótese
confirmatória pré-registrada. Como o BM25 também foi superior no conjunto de
desenvolvimento, ele foi selecionado e integrado como recuperador principal. O método
denso foi preservado como opção de comparação.

| Conjunto | Método | Hit@1 | Hit@8 | MRR | Página exata | Página ±1 |
|---|---|---:|---:|---:|---:|---:|
| Desenvolvimento | BM25 | 88,1% (37/42) | 97,6% (41/42) | 0,917 | 85,7% (36/42) | 90,5% (38/42) |
| Desenvolvimento | Denso | 76,2% (32/42) | 92,9% (39/42) | 0,818 | 71,4% (30/42) | 78,6% (33/42) |
| Final | BM25 | 97,6% (41/42) | 100,0% (42/42) | 0,988 | 73,8% (31/42) | 76,2% (32/42) |
| Final | Denso | 64,3% (27/42) | 83,3% (35/42) | 0,713 | 50,0% (21/42) | 52,4% (22/42) |

No conjunto final, o BM25 superou o recuperador denso em todas as métricas
apresentadas. A diferença foi especialmente alta no primeiro resultado: o documento
esperado apareceu na primeira posição em 41 das 42 perguntas com o BM25, contra 27
com a busca densa. Em `k=8`, o baseline lexical recuperou o documento esperado nas 42
perguntas, enquanto o recuperador denso o recuperou em 35.

Esse resultado não demonstra que a busca lexical seja superior em qualquer corpus.
Ele indica que, neste acervo e neste benchmark, as perguntas e os TCCs compartilham
termos suficientemente discriminativos para favorecer correspondências lexicais. O
resultado também mostra que não é adequado caracterizar o recuperador denso como bom
apenas por seu valor absoluto: a comparação com uma referência simples revela espaço
para substituição ou para uma estratégia híbrida. Uma avaliação futura pode combinar
BM25 e embeddings, mas esse sistema híbrido deve ser tratado como nova configuração e
avaliado sem reajuste sobre o conjunto final já utilizado.

## Decisão de responder ou recusar na execução histórica densa

No conjunto final, o sistema respondeu a 34 das 42 perguntas com resposta no acervo e
recusou corretamente as oito perguntas sem resposta. Isso corresponde a recall de
80,95% para as perguntas com resposta. Não foram observados falsos positivos nas oito
perguntas negativas, mas essa quantidade é pequena: pela regra de três, zero ocorrências
em oito observações ainda é compatível, de modo aproximado, com uma taxa real de até
37,5% no limite superior de 95%. Por isso, o resultado deve ser descrito como “nenhum
falso positivo observado em oito casos”, e não como evidência de precisão perfeita em
uso real.

O cálculo pontual, condicionado à ausência de falso positivo, produz F1 de 89,47%,
mas esse resumo depende da precisão estimada com poucos casos negativos. Se as oito
perguntas negativas da amostra fossem falsos positivos, mantendo-se os demais
resultados, a precisão e a F1 seriam 80,95%. Assim, a F1 pode ser apresentada como uma
análise de sensibilidade entre 80,95% e 89,47% dentro dos cenários desta amostra, sem
afirmar que essa faixa constitui um intervalo de confiança para o uso real. A
prevalência de perguntas com e sem resposta em uso corrente também pode ser diferente
da proporção fixada no benchmark.

A acurácia observada foi de 84% (42/50). Esse valor é igual ao baseline trivial que
responde a todas as perguntas, pois 42 das 50 perguntas têm resposta no acervo.
Entretanto, os erros são diferentes: o baseline “responder sempre” teria oito falsos
positivos e nenhuma recusa indevida, enquanto o sistema teve oito recusas indevidas e
nenhum falso positivo. Portanto, a acurácia não deve ser interpretada isoladamente; o
recall e as contagens da matriz de confusão mostram com mais clareza o comportamento
do sistema.

## Limitações

O gabarito associa cada pergunta a um único documento esperado. Caso outro TCC também
contenha uma resposta válida, a recuperação desse documento alternativo é contada
como erro, o que pode subestimar o desempenho tanto do BM25 quanto do recuperador
denso. Além disso, a comparação mede recuperação de evidências, não a correção factual
das respostas geradas. Essas limitações devem permanecer explícitas na síntese e na
conclusão.
