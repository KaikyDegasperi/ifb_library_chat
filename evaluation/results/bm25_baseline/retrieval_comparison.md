# Comparação do recuperador denso com o baseline BM25

O BM25 e o recuperador denso foram avaliados com as mesmas perguntas, os mesmos
chunks e `k=8`. As métricas de recuperação usam somente as perguntas com
resposta no acervo. O BM25 usa `k1=1.5` e
`b=0.75`, sem stemming e sem remoção de stopwords. O baseline
foi acrescentado retrospectivamente, depois da avaliação original, e seus parâmetros
convencionais não foram ajustados no conjunto final.

| Divisão | Método | Hit@1 | Hit@8 | MRR | Página exata | Página ±1 | Latência média (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| development | BM25 | 88.1% | 97.6% | 0.917 | 85.7% | 90.5% | 6.98 |
| development | Denso | 76.2% | 92.9% | 0.818 | 71.4% | 78.6% | 12.81 |
| final | BM25 | 97.6% | 100.0% | 0.988 | 73.8% | 76.2% | 8.13 |
| final | Denso | 64.3% | 83.3% | 0.713 | 50.0% | 52.4% | 12.95 |

## Baseline da decisão de responder

Em cada divisão há 42 perguntas com resposta e 8 sem resposta. Um classificador que
sempre decidisse responder teria acurácia de 42/50 = 84%, recall de 100% para a classe
“com resposta” e especificidade de 0% para a classe “sem resposta”. Portanto, a
acurácia do sistema deve ser apresentada junto desse baseline; isoladamente, 84% não
demonstra ganho sobre a regra trivial de sempre responder.

## Limites

- O BM25 compara somente a recuperação; ele não gera respostas nem possui, por si só,
  uma regra de recusa comparável à do pipeline RAG.
- Como o baseline foi incorporado depois da avaliação original, a comparação deve ser
  descrita como retrospectiva, e não como hipótese confirmatória pré-registrada.
- O gabarito registra um único documento esperado por pergunta. Se outro TCC também
  contiver resposta válida, as métricas podem subestimar ambos os recuperadores.
- As oito perguntas negativas por divisão são insuficientes para sustentar uma
  estimativa precisa da taxa de falsos positivos.
