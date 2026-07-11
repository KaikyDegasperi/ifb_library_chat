# IFB Library Chat

Base da API para o chatbot de consulta aos Trabalhos de Conclusão de Curso da
Licenciatura em Matemática do IFB Campus Estrutural.

Nesta etapa o projeto oferece configuração local reproduzível, logging,
persistência do ChromaDB e um endpoint de saúde. A ingestão com Docling e o
pipeline RAG ainda serão implementados.

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
data/processed/ resultados da futura extração com Docling
data/chroma/    banco vetorial persistente
logs/           logs rotativos da aplicação
tests/          testes automatizados
```

Os conteúdos gerados desses diretóios são ignorados pelo Git; arquivos
`.gitkeep` mantêm a estrutura no repositório.

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
