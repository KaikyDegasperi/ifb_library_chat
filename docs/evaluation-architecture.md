# Arquitetura da avaliação

## Sistema atual

O projeto usa Python 3.14, FastAPI no backend e Streamlit como camada de apresentação. A API inicia com `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` (ou `uv run python main.py`) e o frontend com `API_BASE_URL=http://127.0.0.1:8000 uv run streamlit run frontend/app.py`.

O fluxo de consulta é:

```text
POST /chat → RAGService → BM25 → pool de 24 candidatos → seleção heurística
           → filtro/deduplicação → contexto top-8 → LLM → resposta e fontes
```

O payload mínimo de `POST /chat` é `{"question": "..."}`. Quando `top_k` é
omitido, a API usa `RAG_RETRIEVAL_TOP_K=8`; um override explícito continua aceito.
A resposta pública contém `answer`, `sources`, `retrieval_time_ms` e
`generation_time_ms`.

`POST /search` registra o ranking inicial do recuperador. A avaliação também
registra, separadamente, a ordem das fontes de `/chat`, que corresponde ao contexto
final após seleção, limiar e deduplicação. Hit@k e MRR podem assim ser relatados para
os dois estágios sem tratá-los como equivalentes.

## Ingestão e persistência

`app/ingestion/service.py` usa Docling para converter os PDFs, extrai metadados acadêmicos e grava um documento Docling e uma lista de chunks em `data/processed`. `app/ingestion/chunking.py` usa o `HybridChunker`, respeita seções e aplica fallback por palavras. Os padrões atuais são chunk size 500 e overlap 50.

O recuperador principal é o BM25, selecionado pela comparação experimental. Ele é
construído a partir dos mesmos chunks processados e pode ser trocado pelo recuperador
denso com `RETRIEVAL_PROVIDER=dense`. Os embeddings são gerados por
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, e
`app/vectorstore/service.py` mantém a coleção ChromaDB usada pelo método denso e pelo
catálogo. Não há banco SQL: o catálogo de documentos é derivado dos metadados no
ChromaDB; o manifesto e os artefatos estruturados usam JSON.

Os parâmetros padrão são:

- busca pública: `SEARCH_TOP_K=5` quando o cliente não informa `top_k`;
- candidatos do RAG: `RAG_RETRIEVAL_TOP_K=8`;
- limiar: `RAG_MIN_SIMILARITY=0.35`;
- contexto máximo: `RAG_MAX_CONTEXT_CHARS=12000`;
- modelo gerador: definido por `LLM_PROVIDER` e `LLM_MODEL` (por padrão não configurado).

O prompt em `app/rag/prompts.py` determina que o modelo responda somente com o contexto. Sem contexto suficiente, `RAGService` responde que não encontrou informação relevante nos TCCs. Falhas de recuperação e geração possuem mensagens controladas diferentes.

## Pontos de integração

O pacote `evaluation` é externo às regras do frontend e não modifica os contratos existentes:

1. `evaluation.diagnose` lê cada PDF e reaproveita metadados/chunks produzidos pelo Docling.
2. `evaluation.generate_benchmark` seleciona evidências dos chunks processados e cria apenas candidatos `pending_review`.
3. A revisão ocorre em XLSX. `evaluation.review` importa decisões explícitas; `evaluation.validate_benchmark` bloqueia fontes/páginas inválidas e itens não aprovados.
4. `evaluation.run` valida a configuração efetiva da API antes de usar `/chat` e
   `/search`. O split final exige confirmação e configuração congelada.
5. `evaluation.metrics` calcula recuperação nos dois estágios, matriz de confusão,
   acurácia, precisão, recall, F1, baseline e categorias determinísticas de fontes.
6. `evaluation.report` produz relatórios locais. Notas humanas permanecem separadas de qualquer julgamento automático.

Nenhuma credencial é serializada. A configuração congelada contém somente parâmetros técnicos seguros, versão/hash do prompt, versão do benchmark, seed, revisão Git e data UTC.

## Limites do contrato atual

Como `/chat` e `/search` são duas chamadas, o acervo deve permanecer imutável
durante a execução. O congelamento inclui um fingerprint dos artefatos de chunks, e
o preflight impede que parâmetros apenas registrados sejam confundidos com os usados
pela API.
