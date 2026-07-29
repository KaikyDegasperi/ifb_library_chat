# Arquitetura da avaliação

## Sistema atual

O projeto usa Python 3.14, FastAPI no backend e Streamlit como camada de apresentação. A API inicia com `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` (ou `uv run python main.py`) e o frontend com `API_BASE_URL=http://127.0.0.1:8000 uv run streamlit run frontend/app.py`.

O fluxo de consulta é:

```text
POST /chat → RAGService → BM25 (padrão) ou busca densa → filtro/remoção de duplicatas
           → montagem do contexto → provedor de LLM → resposta e citações
```

O payload de `POST /chat` é `{"question": "...", "top_k": 5, "document_id": null, "title": null}`. A resposta pública contém `answer`, `sources`, `retrieval_time_ms` e `generation_time_ms`. Cada fonte contém `document_id`, `title`, `file_name`, `page_start`, `page_end`, `section`, `chunk_id` e `score`. A paginação preservada pela ingestão é a página real do arquivo PDF, começando em 1.

`POST /search` recebe `query`, `top_k` e filtros opcionais. Além dos metadados e do score, retorna o texto do chunk. A avaliação chama `/chat` para medir a resposta e `/search` para registrar o ranking e os trechos recuperados, pois o contrato de `/chat` não expõe o conteúdo dos chunks.

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

- busca pública: `SEARCH_TOP_K=5`;
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
4. `evaluation.run` usa somente as APIs públicas `/chat` e `/search`. O split final exige confirmação e configuração congelada.
5. `evaluation.metrics` calcula métricas sem usar o score como prova de correção: compara nomes de arquivos, interseções de páginas e recusas explícitas.
6. `evaluation.report` produz relatórios locais. Notas humanas permanecem separadas de qualquer julgamento automático.

Nenhuma credencial é serializada. A configuração congelada contém somente parâmetros técnicos seguros, versão/hash do prompt, versão do benchmark, seed, revisão Git e data UTC.

## Limites do contrato atual

Os tempos internos detalhados existem no objeto interno `RAGObservation`, mas não são públicos. A avaliação registra os tempos públicos de recuperação e geração, o tempo total observado pelo cliente e o tempo separado de `/search`. Como `/chat` e `/search` são duas chamadas, seus rankings podem divergir se o índice mudar entre elas; por isso o acervo e a configuração devem permanecer congelados durante uma execução.
