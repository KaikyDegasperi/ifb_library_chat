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

O provedor de LLM é opcional nesta etapa. Quando `LLM_PROVIDER=none`, o health
check informa `not_configured`, sem tornar indisponíveis a API, o ChromaDB ou o
modelo de embeddings.

## Configuração

| Variável | Padrão | Finalidade |
|---|---|---|
| `APP_NAME` | `IFB Library Chat` | Nome exibido pela API |
| `APP_ENV` | `development` | Identifica o ambiente |
| `LOG_LEVEL` | `INFO` | Nível de logging |
| `DOCUMENTS_DIR` | `pdfs_ifb` | PDFs originais |
| `PROCESSED_DIR` | `data/processed` | Artefatos processados |
| `INGEST_CHUNK_SIZE` | `500` | Tamanho aproximado em palavras |
| `INGEST_CHUNK_OVERLAP` | `50` | Sobreposição em palavras |
| `INGEST_DEVICE` | `auto` | Dispositivo escolhido pelo Docling |
| `CHROMA_DIR` | `data/chroma` | Persistência do ChromaDB |
| `LOGS_DIR` | `logs` | Arquivos de log |
| `CHROMA_COLLECTION` | `ifb_tcc_matematica` | Nome da coleção |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Modelo multilíngue configurado |
| `LLM_PROVIDER` | `none` | Provedor configurado |
| `LLM_BASE_URL` | vazio | URL de provedor compatível |
| `LLM_MODEL` | vazio | Modelo de linguagem |
| `LLM_API_KEY` | vazio | Credencial local; nunca é retornada pela API |

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
