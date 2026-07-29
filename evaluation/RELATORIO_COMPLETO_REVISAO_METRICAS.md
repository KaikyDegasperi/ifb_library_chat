# Avaliação experimental revisada do IFB Library Chat

## 1. Delimitação da avaliação

Esta avaliação examina duas dimensões do IFB Library Chat:

1. a recuperação dos documentos e das páginas utilizados como contexto; e
2. a decisão do sistema de responder ou recusar uma pergunta.

A avaliação não mede a correção factual, a fidelidade, a completude ou a qualidade
textual das respostas geradas. Portanto, os resultados apresentados neste capítulo
não demonstram que as respostas finais estejam factualmente corretas. Eles mostram
apenas se o sistema recuperou as referências previstas no gabarito e se decidiu
responder ou recusar cada pergunta.

Essa delimitação é necessária porque um pipeline RAG pode falhar em etapas diferentes.
O recuperador pode deixar de localizar uma evidência existente, o mecanismo de decisão
pode recusar uma pergunta que o acervo responde e o modelo gerador pode utilizar
incorretamente um contexto adequado. As métricas desta avaliação cobrem as duas
primeiras situações, mas não a terceira.

## 2. Corpus e benchmark

O corpus foi constituído por 43 Trabalhos de Conclusão de Curso da Licenciatura em
Matemática do IFB Campus Estrutural. Um dos documentos não apresentou conteúdo textual
suficiente mesmo após a etapa de extração e OCR. Esse documento foi mantido no
diagnóstico do corpus, mas excluído da elaboração das perguntas com resposta no
acervo.

O benchmark contém 100 perguntas, divididas da seguinte forma:

| Conjunto | Com resposta no acervo | Sem resposta no acervo | Total |
|---|---:|---:|---:|
| Desenvolvimento | 42 | 8 | 50 |
| Final | 42 | 8 | 50 |
| Total | 84 | 16 | 100 |

Cada um dos 42 documentos avaliáveis foi representado por uma pergunta com resposta
no acervo em cada conjunto. As perguntas de desenvolvimento e final foram construídas
com evidências diferentes. Para cada pergunta foram registrados o documento esperado,
as páginas esperadas, um trecho de evidência, a resposta esperada e os fatos
obrigatórios.

O conjunto de desenvolvimento foi destinado à seleção e ao ajuste das configurações.
O conjunto final foi destinado à apresentação dos resultados. A comparação com o
BM25 foi incorporada depois da avaliação original e, por isso, deve ser caracterizada
como uma análise retrospectiva. Foram utilizados parâmetros convencionais do BM25,
sem ajuste no conjunto final.

## 3. Métodos de recuperação comparados

### Estado da integração

Após a comparação no conjunto de desenvolvimento, o BM25 foi incorporado ao projeto
como recuperador padrão por meio da configuração `RETRIEVAL_PROVIDER=bm25`. O índice
lexical é construído com os artefatos `*.chunks.json` ativos, utiliza os mesmos
identificadores de chunks do ChromaDB e é compartilhado pelas rotas de busca e pelo
serviço RAG. A opção `RETRIEVAL_PROVIDER=dense` foi preservada exclusivamente para
reprodução e comparação.

No corpus utilizado nesta avaliação, os índices lexical e denso contêm 2.812 chunks
ativos. A implementação de produção do BM25 reproduziu integralmente os resultados da
avaliação de recuperação: no desenvolvimento, Hit@1 de 88,10% e Hit@8 de 97,62%; no
conjunto final, Hit@1 de 97,62% e Hit@8 de 100%.

### 3.1 Recuperador denso

O recuperador originalmente implementado representa as perguntas e os chunks por
vetores de embeddings. Os candidatos são ordenados de acordo com a similaridade entre
o vetor da pergunta e os vetores dos chunks armazenados no ChromaDB. O modelo de
embeddings utilizado na execução avaliada foi
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

### 3.2 Baseline lexical BM25

Foi implementado um baseline lexical BM25 para estabelecer uma referência simples de
comparação. O BM25 atribui pesos aos termos considerando sua frequência no chunk, sua
raridade no corpus e uma normalização pelo tamanho do texto. A implementação adotou:

- `k1 = 1,5`;
- `b = 0,75`;
- normalização Unicode NFKC;
- conversão para minúsculas;
- ausência de stemming;
- ausência de remoção de stopwords;
- recuperação sobre os mesmos chunks utilizados pelo método denso.

Os valores de `k1` e `b` foram fixados antes da execução do baseline e não foram
otimizados com as perguntas finais. A formulação do BM25 e seus fundamentos podem ser
consultados em Robertson e Zaragoza (2009).

### 3.3 Condições de comparabilidade

Para isolar o efeito do método de recuperação, BM25 e recuperador denso utilizaram:

- o mesmo corpus;
- os mesmos artefatos de extração;
- a mesma segmentação em chunks;
- as mesmas perguntas;
- o mesmo documento e as mesmas páginas esperadas;
- o mesmo limite de oito resultados por pergunta.

Assim, a variável principal da comparação é o método de ranqueamento: lexical no BM25
e semântico no recuperador denso.

## 4. Métricas de recuperação

As métricas de recuperação foram calculadas somente sobre as perguntas com resposta
no acervo.

O `Hit@k`, equivalente ao Document Recall@k neste benchmark com um documento esperado
por pergunta, indica a proporção de perguntas nas quais o documento esperado apareceu
entre os `k` primeiros chunks:

\[
\operatorname{Hit@k} =
\frac{\text{perguntas com o documento esperado entre os }k\text{ primeiros}}
{\text{perguntas com resposta no acervo}}.
\]

O Mean Reciprocal Rank (MRR) considera a posição do primeiro chunk pertencente ao
documento esperado:

\[
\operatorname{MRR} =
\frac{1}{N}\sum_{i=1}^{N}\frac{1}{\operatorname{rank}_i}.
\]

Quando o documento esperado não aparece nos oito resultados, o recíproco da posição é
considerado zero.

A recuperação de página exata indica a proporção de perguntas em que ao menos um dos
oito chunks pertence simultaneamente ao documento esperado e a uma das páginas
registradas no gabarito. Também foi calculada uma versão com tolerância de uma página,
para considerar possíveis diferenças entre a página física do PDF e a numeração
impressa no documento.

## 5. Resultados da recuperação

### 5.1 Conjunto de desenvolvimento

| Método | Hit@1 | Hit@8 | MRR | Página exata | Página ±1 |
|---|---:|---:|---:|---:|---:|
| BM25 | **88,10% (37/42)** | **97,62% (41/42)** | **0,917** | **85,71% (36/42)** | **90,48% (38/42)** |
| Denso | 76,19% (32/42) | 92,86% (39/42) | 0,818 | 71,43% (30/42) | 78,57% (33/42) |

No conjunto de desenvolvimento, o BM25 superou o recuperador denso em todas as
métricas. A diferença foi de 11,91 pontos percentuais em Hit@1, 4,76 pontos
percentuais em Hit@8 e 14,28 pontos percentuais na recuperação de página exata.

Como a escolha entre os métodos pode ser justificada apenas com o conjunto de
desenvolvimento, esses resultados sustentaram a seleção e a integração do BM25 como
recuperador principal do sistema, sem depender dos valores do conjunto final. O
recuperador denso foi preservado como opção configurável para reprodução experimental.

### 5.2 Conjunto final

| Método | Hit@1 | Hit@8 | MRR | Página exata | Página ±1 |
|---|---:|---:|---:|---:|---:|
| BM25 | **97,62% (41/42)** | **100,00% (42/42)** | **0,988** | **73,81% (31/42)** | **76,19% (32/42)** |
| Denso | 64,29% (27/42) | 83,33% (35/42) | 0,713 | 50,00% (21/42) | 52,38% (22/42) |

No conjunto final, o BM25 também apresentou resultados superiores. O documento
esperado apareceu na primeira posição em 41 das 42 perguntas com o BM25 e em 27 com o
recuperador denso, uma diferença de 33,33 pontos percentuais. Considerando os oito
primeiros resultados, o BM25 recuperou o documento esperado nas 42 perguntas, enquanto
o método denso o recuperou em 35.

A recuperação da página exata foi menor do que a recuperação do documento nos dois
métodos. Esse resultado indica que localizar o TCC correto não garante a recuperação
do trecho ou da página registrada no gabarito. Ainda assim, o BM25 superou o método
denso em 23,81 pontos percentuais na recuperação de página exata do conjunto final.

### 5.3 Interpretação

Os resultados não demonstram que a recuperação lexical seja universalmente superior
à recuperação densa. Eles mostram que, neste corpus e para estas perguntas, a
correspondência lexical foi mais eficaz. Uma explicação plausível é que as perguntas
e os TCCs compartilham termos temáticos, nomes de conceitos e expressões
suficientemente discriminativas para que o BM25 localize diretamente os textos
relevantes.

A comparação também impede que o desempenho denso seja caracterizado como “bom”
somente a partir de seus valores absolutos. Quando confrontado com uma referência
simples, o método denso apresentou desempenho inferior. Com base no desenvolvimento,
o BM25 foi selecionado e integrado à versão final do sistema. Outra possibilidade é
uma recuperação híbrida, mas ela constituiria uma nova configuração e precisaria ser
ajustada no desenvolvimento e avaliada em novas perguntas finais.

## 6. Avaliação da decisão de responder ou recusar

### 6.1 Definição das classes

Para esta análise, uma pergunta com resposta no acervo foi considerada um caso
positivo. Uma pergunta sem resposta no acervo foi considerada um caso negativo:

- verdadeiro positivo (VP): o acervo contém a resposta e o sistema responde;
- falso negativo (FN): o acervo contém a resposta, mas o sistema recusa;
- falso positivo (FP): o acervo não contém a resposta, mas o sistema responde;
- verdadeiro negativo (VN): o acervo não contém a resposta e o sistema recusa.

### 6.2 Matriz de confusão da execução avaliada

Os resultados abaixo pertencem à execução original do pipeline com recuperação densa.
Eles não são atribuídos retroativamente à configuração atual com BM25.

| Situação real | Sistema respondeu | Sistema recusou | Total |
|---|---:|---:|---:|
| Com resposta no acervo | 34 (VP) | 8 (FN) | 42 |
| Sem resposta no acervo | 0 (FP) | 8 (VN) | 8 |
| Total | 34 | 16 | 50 |

O principal erro observado foi a recusa indevida. O sistema recusou oito das 42
perguntas que o acervo poderia responder, correspondendo a 19,05% da classe positiva.
Esse erro é especialmente relevante porque interrompe todo o pipeline: mesmo quando a
informação está disponível, nenhuma resposta é apresentada ao usuário.

### 6.3 Recall

O recall mede a proporção das perguntas com resposta no acervo que foram efetivamente
respondidas:

\[
\operatorname{Recall} =
\frac{VP}{VP+FN} =
\frac{34}{34+8} =
80,95\%.
\]

Esse é o resultado mais sólido da avaliação da decisão, pois depende das 42 perguntas
com resposta no acervo, a classe mais bem representada. O valor mostra diretamente a
principal fraqueza do sistema: aproximadamente 19% das perguntas que poderiam ser
respondidas foram recusadas.

### 6.4 Precisão e ausência de falsos positivos

A precisão observada é:

\[
\operatorname{Precisão} =
\frac{VP}{VP+FP} =
\frac{34}{34+0} =
100\%.
\]

Esse valor não deve ser interpretado como evidência de precisão perfeita em uso real.
Havia somente oito oportunidades para observar um falso positivo, correspondentes às
oito perguntas sem resposta no acervo. O resultado adequado a relatar é:

> Não foi observado falso positivo nas oito perguntas sem resposta no acervo
> avaliadas. Dado o tamanho reduzido dessa classe, o resultado não permite afirmar
> precisão perfeita em uso real.

Pela regra de três, quando nenhum evento é observado em `n` tentativas, o limite
superior aproximado de 95% para a taxa do evento é `3/n`. Para oito perguntas:

\[
\frac{3}{8}=37,5\%.
\]

Isso não significa que a taxa real de falsos positivos seja 37,5%. Significa que uma
amostra com zero ocorrências em oito casos ainda é compatível com taxas populacionais
consideravelmente maiores que zero. A regra de três é uma aproximação para o limite
superior e foi apresentada por Hanley e Lippman-Hand (1983) para interpretar
numeradores iguais a zero.

### 6.5 F1 e análise de sensibilidade

A F1 é a média harmônica entre precisão e recall:

\[
F_1 =
2\frac{\operatorname{Precisão}\times\operatorname{Recall}}
{\operatorname{Precisão}+\operatorname{Recall}}.
\]

Com os valores observados:

\[
F_1 =
2\frac{1,00\times0,8095}{1,00+0,8095} =
89,47\%.
\]

Entretanto, a F1 herda a fragilidade da precisão, que foi estimada com apenas oito
perguntas negativas. Para tornar essa dependência explícita, pode-se apresentar a
seguinte análise de sensibilidade, mantendo o recall em 80,95%:

| Precisão considerada | Recall | F1 resultante |
|---:|---:|---:|
| 100,00% | 80,95% | 89,47% |
| 90,00% | 80,95% | 85,24% |
| 80,95% | 80,95% | 80,95% |

O intervalo de 80,95% a 89,47% descreve uma análise de sensibilidade dentro dos
cenários considerados para esta amostra. Ele não é um intervalo de confiança para a
F1 populacional e não permite afirmar que a “F1 verdadeira” esteja necessariamente
nessa faixa. Em uso real, a proporção de perguntas sem resposta no acervo pode ser
diferente da proporção fixada no benchmark.

Apenas a F1 é apresentada entre as medidas \(F_{\beta}\), porque ela atribui o mesmo
peso à precisão e ao recall e funciona como um resumo equilibrado. Medidas como
\(F_{0,5}\) dariam maior importância à precisão; essa escolha seria difícil de
sustentar neste experimento, pois a precisão é justamente a dimensão menos bem
estimada. Valores de \(\beta>1\) dariam maior importância ao recall e poderiam ser
justificados caso a aplicação estabelecesse formalmente que recusas indevidas são
mais graves. Como essa ponderação não foi definida previamente, a F1 é mantida como
resumo e o recall é discutido separadamente como métrica principal.

### 6.6 Acurácia e baseline “responder sempre”

A acurácia do sistema foi:

\[
\operatorname{Acurácia} =
\frac{VP+VN}{N} =
\frac{34+8}{50} =
84\%.
\]

Isoladamente, esse número não constitui evidência de ganho. Como 42 das 50 perguntas
têm resposta no acervo, um baseline que simplesmente respondesse a todas as perguntas
também teria acurácia de 84%:

| Método | VP | FN | FP | VN | Acurácia |
|---|---:|---:|---:|---:|---:|
| Sistema avaliado | 34 | 8 | 0 | 8 | 84% |
| Responder sempre | 42 | 0 | 8 | 0 | 84% |

Embora tenham a mesma acurácia, os métodos cometem erros diferentes. O sistema
avaliado evita respostas indevidas nas oito perguntas negativas, mas recusa oito
perguntas que poderiam ser respondidas. O baseline responde todas as perguntas
positivas, porém também responde indevidamente às oito negativas.

Com a classe “pergunta com resposta no acervo” definida como positiva, o baseline de
responder sempre teria precisão de 84%, recall de 100% e F1 de aproximadamente 91,30%.
Esse F1 superior ao valor observado do sistema não significa que o baseline seja mais
seguro: a F1 ignora os verdadeiros negativos. O exemplo reforça por que nenhuma
métrica isolada deve substituir a matriz de confusão e a discussão dos tipos de erro.

O benefício demonstrado pelo sistema não está em sua acurácia, mas em sua capacidade
de recusar as oito perguntas negativas avaliadas. A quantidade reduzida dessas
perguntas, entretanto, exige cautela na generalização desse resultado.

## 7. Qualidade das respostas geradas

A correção factual das respostas não foi mensurada. Também não foram produzidas
medidas humanas consolidadas de fidelidade, completude ou sustentação das citações.
Consequentemente, não devem aparecer no resumo ou na conclusão afirmações como:

- “as respostas produzidas foram corretas”;
- “o sistema demonstrou alta qualidade de resposta”;
- “as respostas foram fiéis aos documentos”;
- “as citações foram corretas”.

Os resultados de recuperação são uma condição necessária, mas não suficiente, para a
qualidade da resposta. Mesmo com o documento e a página corretos no contexto, o modelo
gerador pode omitir informações, interpretar incorretamente a evidência ou produzir
afirmações não sustentadas.

Para preencher essa lacuna em trabalhos futuros, uma amostra de respostas pode ser
avaliada por dois revisores independentes nos critérios de correção factual,
fidelidade ao contexto, completude e qualidade das citações. A concordância entre os
revisores também deve ser relatada. Enquanto essa etapa não for realizada, a qualidade
das respostas permanece uma dimensão não mensurada.

## 8. Ameaças à validade

### 8.1 Poucas perguntas sem resposta no acervo

Cada conjunto possui somente oito perguntas negativas. Essa quantidade é insuficiente
para estimar com precisão a taxa de falsos positivos. A ausência de falsos positivos
deve ser relatada como uma observação da amostra, e não como uma propriedade
demonstrada do sistema.

### 8.2 Um único documento esperado

O gabarito associa cada pergunta a um único documento esperado. Caso dois ou mais TCCs
contenham evidências válidas para a mesma pergunta, a recuperação de um documento
alternativo é contabilizada como erro. Esse viés tende a subestimar, e não a inflar,
o desempenho dos recuperadores.

Uma avaliação futura pode registrar um conjunto de documentos relevantes para cada
pergunta, em vez de apenas um documento esperado.

### 8.3 Página física e página impressa

A numeração física do PDF pode divergir da numeração impressa no TCC em razão de capas,
folhas de aprovação e elementos pré-textuais. A métrica com tolerância de uma página
reduz parcialmente esse problema, mas não elimina a necessidade de conferir os
documentos manualmente.

### 8.4 Qualidade da extração

Falhas de OCR, páginas sem texto e erros na estrutura produzida pelo Docling podem
impedir a recuperação mesmo quando a informação está visualmente presente no PDF.
Essas falhas pertencem ao pipeline documental e devem ser consideradas na
interpretação dos resultados.

### 8.5 Comparação retrospectiva

O BM25 foi acrescentado após a execução original. Embora seus parâmetros convencionais
não tenham sido ajustados no conjunto final, a comparação não foi definida antes da
primeira observação dos resultados. Portanto, ela deve ser descrita como retrospectiva.

Embora o BM25 tenha sido incorporado ao sistema, o comportamento completo de resposta
e recusa depende também do gerador externo e deve ser relatado em uma execução própria.
Para uma avaliação confirmatória rigorosa da versão modificada, deve ser elaborado um
novo conjunto final que não seja utilizado durante o desenvolvimento.

### 8.6 Distribuição artificial das classes

A proporção de 42 perguntas com resposta para oito sem resposta foi definida na
construção do benchmark. A frequência dessas classes em uso real pode ser diferente,
afetando especialmente precisão, acurácia e F1. O recall das perguntas com resposta é
menos dependente dessa prevalência artificial.

## 9. Síntese dos resultados

A avaliação mostrou que o recall da decisão de responder foi de 80,95%. Em termos
absolutos, o sistema respondeu a 34 das 42 perguntas com resposta no acervo e recusou
indevidamente oito. Não foi observado falso positivo nas oito perguntas sem resposta,
mas essa quantidade não permite afirmar precisão perfeita em uso real. A F1 observada
foi de 89,47% e deve ser acompanhada de uma análise de sensibilidade, pois depende da
estimativa frágil da precisão.

A acurácia foi de 84%, o mesmo valor obtido pelo baseline trivial de responder sempre.
Por isso, a acurácia não evidencia ganho quando apresentada isoladamente. A diferença
entre os métodos está na natureza dos erros: o sistema avaliado evitou respostas nas
oito perguntas negativas, mas recusou oito perguntas positivas.

Na recuperação, o BM25 superou o recuperador denso em todas as métricas nos conjuntos
de desenvolvimento e final. No desenvolvimento, o BM25 obteve Hit@1 de 88,10% e
Hit@8 de 97,62%, contra 76,19% e 92,86% do método denso. No conjunto final, obteve
Hit@1 de 97,62% e Hit@8 de 100%, contra 64,29% e 83,33% do método denso. Esses
resultados dão uma referência concreta à avaliação e indicam que a recuperação
lexical foi mais adequada ao corpus avaliado.

## 10. Conclusão revisada

Os resultados não sustentam uma afirmação de precisão perfeita nem uma conclusão
genérica de alta qualidade do sistema. A principal evidência sobre a decisão de
responder é o recall de 80,95%, que revela oito recusas indevidas em 42 perguntas com
resposta no acervo. Embora nenhum falso positivo tenha sido observado nas oito
perguntas negativas, o tamanho reduzido dessa classe impede generalizar o resultado
para o uso real.

A comparação entre recuperadores mostrou que o BM25 foi superior à recuperação densa
no benchmark utilizado. Como a superioridade também foi observada no conjunto de
desenvolvimento, o BM25 foi integrado como recuperador principal do IFB Library Chat.
O método denso permanece disponível por configuração para permitir a reprodução da
comparação. As métricas de decisão desta seção registram a execução original e são
identificadas como tal; a configuração BM25 deve ter seus resultados apresentados
separadamente quando a nova execução completa for relatada.

Por fim, a avaliação não mediu a correção factual das respostas geradas. Os resultados
demonstram desempenho de recuperação e de decisão apenas no corpus e nas perguntas
avaliadas. Essa delimitação, juntamente com a apresentação explícita das recusas
indevidas, do baseline lexical, do baseline de responder sempre e das ameaças à
validade, fornece uma interpretação mais realista e verificável do sistema.

## 11. Texto curto para o resumo do TCC

> A avaliação considerou a recuperação de documentos e páginas e a decisão de
> responder ou recusar, sem medir a correção factual das respostas geradas. Na
> configuração original, o sistema respondeu a 34 das 42 perguntas com resposta no
> acervo, correspondendo a recall de 80,95%, e não apresentou falso positivo nas oito
> perguntas sem resposta avaliadas. O pequeno número de casos negativos não permite
> afirmar precisão perfeita em uso real. A acurácia foi de 84%, igual à do baseline
> de responder sempre. Na comparação de recuperação, o BM25 superou o método denso no
> conjunto final, com Hit@1 de 97,62% contra 64,29% e Hit@8 de 100% contra 83,33%.
> Os resultados indicam a adequação do BM25 ao corpus, mas não demonstram a correção
> factual das respostas produzidas.

## 12. Respostas preparadas para a banca

### Por que não afirmar precisão de 100%?

Porque foram avaliadas somente oito perguntas sem resposta no acervo. O resultado
observado foi zero falso positivo em oito casos, mas uma amostra tão pequena não
permite concluir que a taxa populacional seja zero. Pela regra de três, o limite
superior aproximado de 95% seria 37,5%.

### Por que destacar o recall?

Porque ele utiliza as 42 perguntas com resposta no acervo e mede diretamente a falha
mais frequente: a recusa indevida. O recall de 80,95% significa que aproximadamente
19% das perguntas que poderiam ser respondidas foram recusadas.

### Por que apresentar somente a F1 entre as medidas \(F_{\beta}\)?

Porque a F1 equilibra precisão e recall sem introduzir uma preferência adicional que
não foi definida previamente. A \(F_{0,5}\) privilegiaria a precisão, justamente a
métrica estimada com a classe menos representada. Se a aplicação formalizasse que as
recusas indevidas são mais graves, uma medida com \(\beta>1\) poderia ser considerada,
mas essa escolha deveria ser estabelecida antes da avaliação.

### Por que a acurácia de 84% não é suficiente?

Porque o baseline que responde a todas as perguntas também acerta 42 dos 50 casos e
obtém 84%. A acurácia não mostra que o sistema e o baseline erram casos diferentes.
Por isso, ela deve ser apresentada com as matrizes de confusão.

### Por que o BM25 foi melhor?

Neste corpus, as perguntas compartilham termos específicos e discriminativos com os
TCCs. O BM25 se beneficia dessas correspondências lexicais. Isso não demonstra
superioridade universal, apenas maior adequação ao corpus e ao benchmark avaliados.

### O BM25 já é o sistema final?

Sim. O BM25 foi selecionado com base no conjunto de desenvolvimento e integrado como
recuperador padrão do chatbot. O recuperador denso foi mantido como opção configurável
para comparação. As métricas históricas de recusa permanecem identificadas como
resultados da execução densa e não são atribuídas retroativamente ao BM25.

### As respostas do chatbot são factualmente corretas?

Essa dimensão não foi medida. A avaliação mostrou se o sistema recuperou documentos e
páginas previstos e se respondeu ou recusou. Uma avaliação factual exige revisão
humana ou outro protocolo específico para as respostas geradas.

## 13. Padronização da linguagem

Em todo o capítulo e nas tabelas, devem ser utilizadas as expressões:

- “perguntas com resposta no acervo”; e
- “perguntas sem resposta no acervo”.

Devem ser evitadas as formas “perguntas respondíveis” e “perguntas não respondíveis”,
que, embora compreensíveis, são menos naturais e menos diretas.

## Referências sugeridas

HANLEY, James A.; LIPPMAN-HAND, Abby. If nothing goes wrong, is everything all
right? Interpreting zero numerators. *JAMA*, v. 249, n. 13, p. 1743–1745, 1983.
DOI: 10.1001/jama.1983.03330370053031.

ROBERTSON, Stephen; ZARAGOZA, Hugo. The probabilistic relevance framework: BM25 and
beyond. *Foundations and Trends in Information Retrieval*, v. 3, n. 4, p. 333–389,
2009. DOI: 10.1561/1500000019.

VAN RIJSBERGEN, Cornelis Joost. *Information Retrieval*. 2. ed. London:
Butterworths, 1979.
