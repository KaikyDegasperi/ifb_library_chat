# Texto-base para a avaliação experimental do TCC

> Este texto deve substituir a afirmação da seção 7.10.5 de que não houve
> avaliação quantitativa. Os campos entre colchetes somente podem ser preenchidos
> depois da execução final e da revisão humana.

## Avaliação experimental

A avaliação do IFB Library Chat foi organizada de modo a separar o componente de
recuperação documental da etapa de geração da resposta. Essa separação é necessária
porque uma resposta inadequada pode decorrer tanto da ausência de evidência relevante
entre os trechos recuperados quanto da utilização incorreta de um contexto adequado
pelo modelo de linguagem.

O corpus avaliado foi composto por 43 Trabalhos de Conclusão de Curso da Licenciatura
em Matemática do IFB Campus Estrutural. Antes dos experimentos, os PDFs foram
submetidos a diagnóstico estrutural e conferência dos artefatos produzidos pelo Docling.
Foram registradas a quantidade de páginas, a disponibilidade de texto extraível, as
páginas vazias e a necessidade provável de OCR. Essa etapa permitiu tratar a qualidade
dos documentos como uma possível ameaça à validade dos resultados.

Um dos 43 PDFs não apresentou conteúdo textual suficiente mesmo após a etapa de OCR,
produzindo apenas informações de capa e aprovação. Esse documento foi mantido no
diagnóstico do corpus, mas excluído, com justificativa registrada, da avaliação de
respostas. Foi construído um benchmark com 100 perguntas. Cada um dos 42 TCCs
avaliáveis foi representado por uma pergunta respondível no conjunto de desenvolvimento e por outra pergunta
respondível, baseada em evidência diferente, no conjunto final. Foram acrescentadas
oito perguntas sem resposta no acervo em cada conjunto, totalizando 50 casos de
desenvolvimento e 50 casos finais. Para cada pergunta respondível foram registrados o
PDF esperado, as páginas, o trecho de evidência, os fatos obrigatórios, o tipo da
pergunta e o grau de dificuldade. Todos os candidatos foram conferidos manualmente no
documento original antes da aprovação.

O conjunto de desenvolvimento foi utilizado para ajustes de segmentação, quantidade
de resultados recuperados, limiar de similaridade e prompt. Após esses ajustes, foram
congelados a versão do código, o modelo de embeddings, o modelo gerador, o prompt e os
demais parâmetros. O conjunto final permaneceu separado e foi executado uma única vez,
reduzindo o risco de ajuste do sistema às perguntas usadas para relatar o desempenho.

Na recuperação foram calculados Document Recall@1, Document Recall@3, Document
Recall@k, Page Recall@k e Mean Reciprocal Rank (MRR). A geração foi avaliada
manualmente em escala ordinal de zero a dois nos critérios de correção, fidelidade ao
contexto, completude e qualidade das citações. Também foram calculadas a taxa de recusa
correta para perguntas externas ao acervo, a taxa de recusa indevida, a média, a
mediana e o percentil 95 do tempo de resposta, além do total de erros e timeouts.

Para reduzir a subjetividade da avaliação das respostas, [N] casos foram avaliados de
forma independente por dois revisores. A concordância foi de [VALOR E MÉTRICA], e as
divergências foram resolvidas por consenso. Nenhuma pergunta ou resposta esperada do
conjunto final foi modificada depois da execução.

## Resultados

No conjunto final, o sistema obteve Document Recall@1 de [VALOR], Document Recall@3
de [VALOR], Document Recall@k de [VALOR], Page Recall@k de [VALOR] e MRR de [VALOR].
Esses valores indicam [INTERPRETAÇÃO LIMITADA AOS DADOS].

As médias das notas humanas foram [VALOR]/2 para correção, [VALOR]/2 para fidelidade,
[VALOR]/2 para completude e [VALOR]/2 para qualidade das citações. A taxa de recusa
correta foi [VALOR], enquanto a recusa indevida ocorreu em [VALOR] das perguntas
respondíveis. O tempo mediano foi [VALOR] ms e o percentil 95 foi [VALOR] ms. Foram
observados [N] erros e [N] timeouts.

Os resultados devem ser interpretados no escopo do corpus fechado e das perguntas
aprovadas. A avaliação não demonstra correção universal do modelo e não substitui um
estudo de usabilidade com participantes. Documentos digitalizados, falhas de OCR,
escolhas de segmentação e a subjetividade residual das notas humanas constituem
ameaças à validade.

## Ajuste necessário na conclusão

A frase atual que afirma genericamente que “a avaliação realizada” demonstrou qualidade
deve ser substituída pelos valores do conjunto final. Caso alguma dimensão apresente
resultado baixo, ela deve ser relatada como limitação e não omitida.
