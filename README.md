# IFB Library Chat

Base da API para o chatbot de consulta aos Trabalhos de Conclusão de Curso da
Licenciatura em Matemática do IFB Campus Estrutural.

Nesta etapa o projeto oferece configuração local reproduzível, logging,
persistência do ChromaDB, um endpoint de saúde e ingestão estruturada de PDFs
com Docling. A indexação vetorial e o pipeline RAG ainda serão implementados.

## Requisitos

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Instalação

Clone o repositório, entre na pasta e execute:

```bash
uv sync
cp .env.example .env
```

O `uv sync` instala a aplicação e o grupo de desenvolvimento, incluindo os
testes. Para instalar também o scraper:

```bash
uv sync --group scraper
uv run playwright install chromium
```

Nenhuma chave real deve ser colocada em `.env.example`. O arquivo `.env` local
é ignorado pelo Git.

## Execução da API

```bash
uv run uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Alternativamente:

```bash
uv run python main.py
```

A documentação interativa fica em `http://127.0.0.1:8000/docs` e o health
check em `http://127.0.0.1:8000/health`.

Exemplo:

```bash
curl --fail http://127.0.0.1:8000/health
```

Endpoints disponíveis:

```text
GET    /health
GET    /documents
GET    /documents/{document_id}
POST   /documents/ingest
DELETE /documents/{document_id}
POST   /search
POST   /chat
```

Exemplo de busca sem geração:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"tecnologia no ensino de matemática","top_k":5}'
```

Exemplo de conversa RAG:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Quais TCCs discutem tecnologia?","top_k":5}'
```

Upload e ingestão:

```bash
curl -X POST http://127.0.0.1:8000/documents/ingest \
  -F 'file=@trabalho.pdf;type=application/pdf'
```

Para um PDF que já esteja dentro de `DOCUMENTS_DIR`:

```bash
curl -X POST http://127.0.0.1:8000/documents/ingest \
  -F 'path=trabalho.pdf'
```

O upload aceita apenas nomes seguros, extensão `.pdf`, MIME type de PDF,
assinatura `%PDF-` e arquivos dentro do limite configurado. Caminhos absolutos e
tentativas de sair de `DOCUMENTS_DIR` são rejeitados.

O provedor de LLM é opcional nesta etapa. Quando `LLM_PROVIDER=none`, o health
check informa `not_configured`, sem tornar indisponíveis a API, o ChromaDB ou o
modelo de embeddings.

## Configuração

| Variável | Padrão | Finalidade |
|---|---|---|
| `APP_NAME` | `IFB Library Chat` | Nome exibido pela API |
| `APP_ENV` | `development` | Identifica o ambiente |
| `LOG_LEVEL` | `INFO` | Nível de logging |
| `MAX_UPLOAD_SIZE_MB` | `25` | Tamanho máximo aceito no upload de PDF |
| `DOCUMENTS_DIR` | `pdfs_ifb` | PDFs originais |
| `PROCESSED_DIR` | `data/processed` | Artefatos processados |
| `INGEST_CHUNK_SIZE` | `500` | Tamanho aproximado em palavras |
| `INGEST_CHUNK_OVERLAP` | `50` | Sobreposição em palavras |
| `INGEST_DEVICE` | `auto` | Dispositivo escolhido pelo Docling |
| `CHROMA_DIR` | `data/chroma` | Persistência do ChromaDB |
| `LOGS_DIR` | `logs` | Arquivos de log |
| `CHROMA_COLLECTION` | `ifb_tcc_matematica` | Nome da coleção |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Modelo multilíngue configurado |
| `EMBEDDING_BATCH_SIZE` | `32` | Textos processados por lote de embeddings |
| `SEARCH_TOP_K` | `5` | Quantidade padrão de resultados da busca |
| `LLM_PROVIDER` | `none` | Provedor configurado |
| `LLM_BASE_URL` | vazio | URL de provedor compatível |
| `LLM_MODEL` | vazio | Modelo de linguagem |
| `LLM_API_KEY` | vazio | Credencial local; nunca é retornada pela API |
| `LLM_TIMEOUT_SECONDS` | `30` | Tempo máximo para geração |
| `RAG_RETRIEVAL_TOP_K` | `8` | Candidatos recuperados antes da seleção |
| `RAG_MIN_SIMILARITY` | `0.35` | Similaridade mínima aceita como contexto |
| `RAG_MAX_CONTEXT_CHARS` | `12000` | Limite total do contexto enviado ao LLM |
| `RAG_MAX_QUESTION_CHARS` | `2000` | Limite da pergunta |
| `RAG_DUPLICATE_THRESHOLD` | `0.92` | Limiar para remover chunks quase idênticos |

O health check verifica que o pacote de embeddings e o nome do modelo estão
disponíveis. Os pesos do modelo serão baixados apenas quando a futura etapa de
ingestão ou consulta carregar efetivamente o modelo.

## Diretórios de dados

```text
pdfs_ifb/       documentos PDF originais
data/processed/ documentos estruturados e chunks gerados pelo Docling
data/chroma/    banco vetorial persistente
logs/           logs rotativos da aplicação
tests/          testes automatizados
```

Os conteúdos gerados desses diretórios são ignorados pelo Git; arquivos
`.gitkeep` mantêm a estrutura no repositório.

## Ingestão de PDFs com Docling

Para processar o diretório configurado em `DOCUMENTS_DIR`:

```bash
uv run python -m app.cli.ingest
```

Para processar um PDF ou diretório específico:

```bash
uv run python -m app.cli.ingest \
  --input ./pdfs_ifb \
  --output ./data/processed \
  --chunk-size 500 \
  --overlap 50 \
  --device auto
```

O tamanho e a sobreposição são aproximados em palavras. O chunker preserva os
limites estruturais produzidos pelo Docling e subdivide somente elementos que
ultrapassam o limite configurado. A sobreposição nunca combina seções distintas.

Para cada documento são gravados:

```text
<document_id>.docling.json    documento estruturado original do Docling
<document_id>.chunks.json     chunks e metadados prontos para embeddings
manifest.json                 hashes e artefatos usados para deduplicação
last-ingestion-report.json    resultado do lote mais recente
```

Na primeira execução, o Docling pode baixar modelos oficiais de layout e
tabelas. Execuções posteriores reutilizam o cache local. Um PDF sem alterações
é ignorado quando seus dois artefatos ainda existem.

## Indexação vetorial

Depois da ingestão, indexe os arquivos `*.chunks.json` no ChromaDB persistente:

```bash
uv run python -m app.cli.index \
  --input ./data/processed \
  --chroma-dir ./data/chroma \
  --collection ifb_tcc_matematica
```

O modelo configurado por `EMBEDDING_MODEL` é carregado por uma implementação
isolada da interface de embeddings. Na primeira execução, seus pesos podem ser
baixados. IDs derivados do hash, índice e conteúdo do chunk evitam duplicações.
Quando a mesma origem possui versões diferentes, apenas a mais recente é
selecionada e os chunks obsoletos são removidos.

Consulta de teste:

```bash
uv run python -m app.cli.search \
  "Como a discalculia afeta a aprendizagem?" \
  --top-k 5
```

Filtros opcionais:

```bash
uv run python -m app.cli.search \
  "ensino de geometria" \
  --document-id d497a407dea443a3

uv run python -m app.cli.search \
  "educação inclusiva" \
  --title "Título exato do trabalho"
```

Cada resultado inclui similaridade, documento, arquivo, páginas, seção, hash
e caminho do PDF original.

## Pipeline RAG

O serviço RAG é independente da API HTTP. Ele valida a pergunta, consulta o
ChromaDB, descarta resultados abaixo do limiar, remove trechos quase idênticos,
limita o contexto e chama o provedor de linguagem configurado.

Configuração de um endpoint compatível com a API de chat da OpenAI:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://provedor.example/v1
LLM_MODEL=nome-do-modelo
LLM_API_KEY=
```

Provedores locais compatíveis que não exigem chave podem deixar
`LLM_API_KEY` vazio. Nenhuma credencial é escrita no código ou nos logs.

Uso pela camada de aplicação:

```python
from app.config import get_settings
from app.rag.factory import create_rag_service

rag = create_rag_service(get_settings())
response = rag.answer("O que os TCCs dizem sobre discalculia?")
```

Quando não há resultado com similaridade suficiente, o LLM não é chamado.
Falhas e timeouts na geração retornam uma mensagem controlada junto das fontes
recuperadas.

## Testes

```bash
uv run pytest
```

## Scraper

Com o grupo `scraper` instalado e o Chromium disponível:

```bash
uv run python scraper/tcc_ifbs_licenciatura_em_matematica.py
```

O scraper existente usa navegador com interface gráfica e salva os PDFs em
`pdfs_ifb/` quando executado a partir da raiz do projeto.
