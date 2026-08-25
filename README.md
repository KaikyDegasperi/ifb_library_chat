# IFB Library Chat

Base da API para o chatbot de consulta aos Trabalhos de Conclusão de Curso da
Licenciatura em Matemática do IFB Campus Estrutural.

O projeto oferece configuração local reproduzível, logging, ingestão estruturada
com Docling, indexação persistente no ChromaDB, recuperação lexical BM25, pipeline RAG e
uma interface Streamlit para consulta e administração do acervo.

## Requisitos

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Instalação

Clone o repositório, entre na pasta e execute:

```bash
uv sync --locked
cp .env.example .env
```

Gere um token administrativo aleatório e coloque o valor somente no `.env` local:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```dotenv
ADMIN_API_TOKEN=cole-aqui-o-valor-gerado
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

O alias abaixo inicia a mesma aplicação e é o comando recomendado para uso
com a interface Streamlit:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
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

`GET /health`, `GET /documents`, `GET /documents/{document_id}`, `POST /search`
e `POST /chat` são públicos. Upload, ingestão e exclusão exigem o header
`Authorization: Bearer <token>`. O token nunca deve ser colocado na URL.

Exemplo de busca sem geração:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"tecnologia no ensino de matemática"}'
```

Exemplo de conversa RAG:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Quais TCCs discutem tecnologia?"}'
```

Upload e ingestão:

```bash
curl -X POST http://127.0.0.1:8000/documents/ingest \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -F 'file=@trabalho.pdf;type=application/pdf'
```

Para um PDF que já esteja dentro de `DOCUMENTS_DIR`:

```bash
curl -X POST http://127.0.0.1:8000/documents/ingest \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -F 'path=trabalho.pdf'
```

Exclusão administrativa:

```bash
curl -X DELETE http://127.0.0.1:8000/documents/ID_DO_DOCUMENTO \
  -H "Authorization: Bearer $ADMIN_API_TOKEN"
```

O upload aceita apenas nomes seguros, extensão `.pdf`, MIME type de PDF,
assinatura `%PDF-` e arquivos dentro do limite configurado. Caminhos absolutos e
tentativas de sair de `DOCUMENTS_DIR` são rejeitados.

O provedor de LLM é opcional nesta etapa. Quando `LLM_PROVIDER=none`, o health
check informa `not_configured`, sem tornar indisponíveis a API, o ChromaDB ou o
modelo de embeddings.

## Interface Streamlit

A interface é uma camada de apresentação separada. Ela não acessa Docling,
ChromaDB, embeddings ou serviços internos; todas as operações usam HTTP:

```text
Navegador → Streamlit → FastAPI → serviços RAG e de ingestão
```

Inicie os dois processos em terminais separados.

Ou inicie API e interface juntas com o script local:

```bash
./scripts/run-local.sh
```

Use `Ctrl+C` para encerrar os dois processos. As portas podem ser alteradas com
`API_PORT` e `STREAMLIT_PORT`.

Terminal 1:

```bash
uv run uvicorn app.main:app --reload
```

Terminal 2:

```bash
API_BASE_URL=http://127.0.0.1:8000 uv run streamlit run frontend/app.py
```

A interface fica em `http://localhost:8501`. `API_BASE_URL` é opcional e usa
`http://127.0.0.1:8000` por padrão.

Ela oferece duas áreas:

- **Consultar acervo:** estado da API, quantidade de documentos, histórico,
  chat e fontes expansíveis;
- **Gerenciar documentos:** upload PDF, acompanhamento da ingestão, listagem,
  confirmação e exclusão.

O token é solicitado somente ao abrir **Gerenciar documentos**. Ele permanece no
estado da sessão daquela aba, não é exibido depois do envio e não é gravado em
arquivo, URL ou log. Um token negado é descartado da sessão.

## Configuração

| Variável | Padrão | Finalidade |
|---|---|---|
| `APP_NAME` | `IFB Library Chat` | Nome exibido pela API |
| `APP_ENV` | `development` | Identifica o ambiente |
| `LOG_LEVEL` | `INFO` | Nível de logging |
| `METRICS_DETAILS_ENABLED` | `false` | Inclui tempos por etapa nos logs do RAG |
| `API_DOCS_ENABLED` | automático | Habilita OpenAPI; padrão ligado em desenvolvimento e desligado em produção |
| `CORS_ALLOWED_ORIGINS` | `[]` | Allowlist JSON de origens autorizadas no navegador |
| `SEARCH_MAX_QUERY_CHARS` | `2000` | Limite da consulta em `/search` |
| `API_MAX_TOP_K` | `50` | Maior `top_k` aceito por `/search` e `/chat` |
| `API_MAX_FILTER_CHARS` | `500` | Limite de `document_id` e `title` nas consultas |
| `MAX_UPLOAD_SIZE_MB` | `25` | Tamanho máximo aceito no upload de PDF |
| `MAX_REQUEST_SIZE_MB` | `30` | Limite da requisição HTTP declarada, incluindo multipart |
| `MAX_UPLOAD_FILENAME_CHARS` | `180` | Tamanho máximo do nome de PDF |
| `ADMIN_API_TOKEN` | vazio | Token Bearer exigido nas operações administrativas |
| `DOCUMENTS_DIR` | `pdfs_ifb` | PDFs originais |
| `PROCESSED_DIR` | `data/processed` | Artefatos processados |
| `INGEST_CHUNK_SIZE` | `500` | Limite aproximado de tokens por chunk |
| `INGEST_CHUNK_OVERLAP` | `50` | Sobreposição em palavras no fallback final |
| `INGEST_DEVICE` | `auto` | Dispositivo escolhido pelo Docling |
| `CHROMA_DIR` | `data/chroma` | Persistência do ChromaDB |
| `LOGS_DIR` | `logs` | Arquivos de log |
| `CHROMA_COLLECTION` | `ifb_tcc_matematica` | Nome da coleção |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Modelo multilíngue configurado |
| `EMBEDDING_BATCH_SIZE` | `32` | Textos processados por lote de embeddings |
| `RETRIEVAL_PROVIDER` | `bm25` | Recuperador principal (`bm25` ou `dense`) |
| `BM25_K1` | `1.5` | Saturação da frequência de termos no BM25 |
| `BM25_B` | `0.75` | Normalização por tamanho do chunk no BM25 |
| `SEARCH_TOP_K` | `5` | Quantidade padrão de resultados da busca |
| `LLM_PROVIDER` | `none` | Provedor configurado |
| `LLM_BASE_URL` | vazio | URL de provedor compatível |
| `LLM_MODEL` | vazio | Modelo de linguagem |
| `LLM_API_KEY` | vazio | Credencial local; nunca é retornada pela API |
| `LLM_TIMEOUT_SECONDS` | `30` | Tempo máximo para geração |
| `LLM_TEMPERATURE` | `0.1` | Temperatura usada pelo gerador |
| `LLM_TOP_P` | `0.9` | Amostragem nucleus do gerador |
| `LLM_MAX_TOKENS` | `256` | Limite de tokens da resposta |
| `RAG_RETRIEVAL_TOP_K` | `8` | Trechos mantidos no contexto final; padrão de `/chat` |
| `RAG_CANDIDATE_POOL_SIZE` | `24` | Candidatos recuperados antes da seleção |
| `RAG_LEXICAL_PROMOTION_SLOTS` | `2` | Vagas do top-8 reservadas a promoções lexicais; as demais preservam a ordem BM25 |
| `RAG_MIN_SIMILARITY` | `0.35` | Limiar de relevância; no BM25 incide sobre o score normalizado |
| `RAG_MAX_CONTEXT_CHARS` | `12000` | Limite total do contexto enviado ao LLM |
| `RAG_MAX_QUESTION_CHARS` | `2000` | Limite da pergunta |
| `RAG_DUPLICATE_THRESHOLD` | `0.92` | Limiar para remover chunks quase idênticos |
| `RAG_SPELLING_FALLBACK_ENABLED` | `false` | Refaz consultas sem contexto usando sugestão ortográfica; opcional e fora da avaliação oficial |
| `RAG_VAGUE_QUESTION_HANDLING_ENABLED` | `false` | Solicita refinamento quando a pergunta não contém tema identificável |

Esses recursos conversacionais ficam desativados por padrão para preservar a
reprodução das métricas oficiais. Eles podem ser habilitados somente no `.env`
local, sem modificar as configurações congeladas da avaliação.

Em `APP_ENV=production`, a aplicação falha na inicialização quando
`ADMIN_API_TOKEN` está ausente ou vazio. Em desenvolvimento, as rotas
administrativas ficam desabilitadas e retornam HTTP 503 enquanto nenhum token
estiver configurado. Tokens ausentes ou incorretos retornam HTTP 401 com uma
mensagem genérica, sem revelar a credencial esperada.

`CORS_ALLOWED_ORIGINS` usa uma lista JSON, por exemplo
`["https://biblioteca.example"]`. Quando a lista está vazia, a API não permite
chamadas cross-origin feitas diretamente pelo navegador. Em produção, `*` e
origens sem HTTPS são recusadas na inicialização. Cookies e credenciais de origem
cruzada não são habilitados; o token Bearer administrativo continua explícito.

O limite HTTP é aplicado ao `Content-Length` declarado e também ao corpo
efetivamente recebido. O reverse proxy deve repetir esse limite para rejeitar a
requisição antes que ela alcance o processo da aplicação.

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

O tamanho é um limite aproximado de tokens, alinhado ao tokenizer do modelo de
embeddings. O `HybridChunker` preserva a estrutura produzida pelo Docling, une
blocos pequenos da mesma seção e subdivide os que ultrapassam o limite. A etapa
final por palavras mantém a sobreposição configurada quando ainda for necessário
dividir um bloco excepcionalmente grande.

Durante a conversão, o pipeline também:

- identifica título, autoria, orientação, coorientação e ano a partir da capa e da
  ficha de aprovação;
- enriquece fórmulas e classifica figuras;
- remove do índice vetorial folhas administrativas do SUAP e fichas de aprovação,
  depois de aproveitar seus metadados;
- reprocessa automaticamente artefatos produzidos por uma versão antiga do
  pipeline.

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

Esse comando é uma operação administrativa local e não atravessa a API HTTP.
Caso uma rota HTTP de reindexação seja adicionada futuramente, ela deve usar o
mesmo sub-roteador administrativo protegido por Bearer token.

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

Cada resultado inclui pontuação de relevância, documento, arquivo, páginas, seção, hash
e caminho do PDF original.

## Diagnóstico ponta a ponta do acervo

Execute a verificação dos PDFs, artefatos Docling, chunks e índice persistente:

```bash
uv run python -m app.cli.diagnose
```

O comando é somente leitura por padrão. Ele calcula os hashes dos PDFs, confere
os arquivos `.docling.json` e `.chunks.json`, lê metadados e documentos da
coleção existente e executa três sondagens vetoriais usando embeddings já
armazenados. As sondagens confirmam que a busca devolve chunks rastreáveis para
um PDF existente e para páginas presentes no artefato Docling, sem depender de
perguntas acadêmicas predefinidas e sem chamar o LLM.

O relatório JSON inclui:

- estado geral `ok` ou `issues`, adequado para automação;
- quantidade de PDFs e hashes únicos;
- documentos processados, com chunks e indexados;
- situação individual de cada documento nas três etapas;
- total, média e mediana de chunks por documento único, incluindo zero para
  documentos sem chunks;
- artefatos ausentes ou inválidos, chunks vazios e metadados acadêmicos ausentes;
- PDFs duplicados por SHA-256;
- documentos sem páginas indexadas;
- chunks órfãos, ausentes ou vazios no ChromaDB;
- resultado das sondagens e configuração efetivamente utilizada.

Diretórios e quantidade de sondagens podem ser informados explicitamente:

```bash
uv run python -m app.cli.diagnose \
  --documents-dir ./pdfs_ifb \
  --processed-dir ./data/processed \
  --chroma-dir ./data/chroma \
  --collection ifb_tcc_matematica \
  --probe-count 3
```

A única operação mutável oferecida pelo comando é a reindexação, que exige
a opção explícita abaixo e pode carregar ou baixar o modelo de embeddings:

```bash
uv run python -m app.cli.diagnose --reindex
```

Nenhuma das formas modifica ou remove os PDFs originais. O comando retorna zero
somente quando o estado geral é `ok`, e retorna 1 quando encontra inconsistências.
Sem `--reindex`, uma
coleção ausente não é criada: o relatório marca o ChromaDB como indisponível e o
comando termina com código 1. Erros de entrada terminam com código 2.

## Pipeline RAG

O pipeline oficial usa recuperação lexical BM25 (`k1=1,5`, `b=0,75`). O serviço
recupera um pool de 24 candidatos, aplica o limiar e a deduplicação e preserva seis
âncoras na ordem BM25. As duas vagas restantes podem promover candidatos pela
cobertura lexical, sem eliminar as âncoras. O contexto continua limitado a oito
trechos e seu orçamento de caracteres é distribuído entre todos os selecionados.
Essa regra é uma mudança metodológica calibrada no split de desenvolvimento.
O recuperador denso permanece disponível somente para reprodução dos experimentos
históricos com `RETRIEVAL_PROVIDER=dense`.

`POST /chat` separa `retrieved_context`, usado para auditoria da seleção, de
`sources`, que contém somente fontes citadas inline na resposta. Recusas e falhas de
geração nunca expõem fontes públicas; o contexto recuperado permanece auditável.

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

Quando não há resultado com relevância suficiente, o LLM não é chamado.
Falhas e timeouts na geração retornam uma mensagem controlada junto das fontes
recuperadas.

## Observabilidade e avaliação

Cada requisição recebe um identificador aleatório, também devolvido no header
`X-Request-ID`. Os logs estruturados registram endpoint, status, duração e tipo
de erro. No fluxo RAG também são registrados quantidade de fontes e tamanho do
contexto. Com `METRICS_DETAILS_ENABLED=true`, o log inclui separadamente os
tempos de embedding, busca no ChromaDB, preparação do contexto e geração pelo
LLM.

O contrato público de `/chat` permanece inalterado. Para experimentos do PCC, o
módulo de avaliação expõe todas as durações a partir da resposta interna:

```python
from app.rag.evaluation import build_evaluation_output

evaluation = build_evaluation_output(response)
print(evaluation.durations.model_dump())
```

Os logs não registram perguntas, contexto integral, PDFs, chaves de API, token
administrativo nem headers de autenticação. Mensagens retornadas por exceções de
provedores externos também não são incluídas.

## Segurança de implantação e armazenamento

Em produção, execute o Uvicorn em uma interface privada ou em
`127.0.0.1:8000` e publique somente um reverse proxy com HTTPS. O proxy, como
Caddy, Nginx ou o serviço gerenciado da instituição, fornece a criptografia em
trânsito, certificado TLS, limite de corpo e políticas de rede. Se um contêiner
precisar usar `0.0.0.0`, a porta da aplicação deve permanecer restrita à rede
interna e não deve ser publicada diretamente na internet.

Use em produção:

```dotenv
APP_ENV=production
ADMIN_API_TOKEN=valor-aleatorio-forte
API_DOCS_ENABLED=false
CORS_ALLOWED_ORIGINS=["https://biblioteca.example"]
```

Sem definição explícita, `/docs`, `/redoc` e `/openapi.json` são desativados em
produção. A aplicação não implementa criptografia própria. A proteção em repouso
depende do ambiente: permissões do sistema, volumes ou discos criptografados,
controle de acesso, backups e descarte definidos pelo IFB.

Política de armazenamento:

- **PDFs:** ficam em `DOCUMENTS_DIR`. Uploads não sobrescrevem nomes existentes,
  duplicatas por SHA-256 são recusadas e temporários são removidos. A exclusão
  administrativa atual remove apenas o índice vetorial, preservando o original;
- **documentos Docling e chunks:** ficam em `PROCESSED_DIR` e podem conter o texto
  integral do trabalho. Devem receber a mesma proteção de acesso e retenção dos
  PDFs;
- **embeddings:** ficam no ChromaDB em `CHROMA_DIR`. São dados derivados, não uma
  forma de anonimização, e devem permanecer no mesmo domínio protegido;
- **logs:** ficam em `LOGS_DIR`, com rotação local. Registram metadados operacionais
  e caminhos de processamento, mas não conteúdo integral, perguntas, prompts,
  chaves ou headers de autenticação. O acesso e a retenção devem ser limitados à
  equipe do PCC;
- **perguntas:** não são persistidas nem registradas pelos logs atuais. Qualquer
  coleta futura exige finalidade definida, aviso aos usuários, minimização,
  retenção e controle de acesso antes de ser habilitada.

Perguntas e documentos são tratados como entrada não confiável no prompt. O
modelo recebe instrução para ignorar tentativas de mudar as regras, revelar
prompts ou executar comandos. Essa defesa reduz prompt injection, mas nenhum
controle baseado apenas em prompt oferece garantia absoluta; respostas devem
continuar limitadas às fontes e observadas durante o PCC.

## Execução com Docker Compose

O Compose preserva a separação da arquitetura:

```text
navegador → frontend:8501 (Streamlit) → api:8000 (FastAPI)
```

Os dois serviços usam a mesma imagem reproduzível, mas executam processos
distintos. A API não é publicada no host por padrão; somente o Streamlit é
exposto em `127.0.0.1:8501`. A comunicação `frontend → api` ocorre apenas pela
rede interna do Compose.

### Configuração e inicialização

Crie o arquivo local de configuração, que é ignorado pelo Git:

```bash
cp .env.docker.example .env.docker
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Coloque o token gerado somente em `ADMIN_API_TOKEN` do `.env.docker`. Depois:

```bash
docker compose config --quiet
docker compose up --build --detach --wait
docker compose ps
```

A interface fica em `http://127.0.0.1:8501`. Para acompanhar os processos:

```bash
docker compose logs --follow api frontend
```

O script abaixo constrói, inicia e consulta os health checks da FastAPI e do
Streamlit:

```bash
./scripts/container-smoke-test.sh
```

### Persistência

Os dados ficam fora da camada gravável dos containers, em volumes nomeados:

| Volume | Conteúdo no container |
|---|---|
| `pdfs_data` | `/data/pdfs` |
| `processed_data` | `/data/processed` |
| `chroma_data` | `/data/chroma` |
| `logs_data` | `/data/logs` |
| `model_cache` | `/home/appuser/.cache` |

`docker compose down` preserva esses volumes. **Não use `docker compose down
-v`** sem um backup, pois essa opção remove os dados persistentes.

Para copiar o acervo local existente, pare os serviços e monte cada origem como
somente leitura:

```bash
docker compose down
docker compose run --rm --no-deps \
  -v "$(pwd)/pdfs_ifb:/source:ro" api \
  sh -c 'cp -R /source/. /data/pdfs/'
docker compose run --rm --no-deps \
  -v "$(pwd)/data/processed:/source:ro" api \
  sh -c 'cp -R /source/. /data/processed/'
docker compose run --rm --no-deps \
  -v "$(pwd)/data/chroma:/source:ro" api \
  sh -c 'cp -R /source/. /data/chroma/'
```

Faça essa cópia do ChromaDB somente com a API parada. Depois, valide sem
alterar o acervo:

```bash
docker compose run --rm api python -m app.cli.diagnose
```

### Provedor de LLM

Para um provedor externo compatível com OpenAI, configure no `.env.docker`:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://provedor.example/v1
LLM_MODEL=nome-do-modelo
LLM_API_KEY=chave-definida-somente-localmente
```

Para Ollama executado na máquina hospedeira:

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=qwen2.5:3b
```

O alias `host.docker.internal` é configurado também no Linux. Se o Ollama estiver
em outro serviço da mesma rede Compose, use `http://ollama:11434`. Nenhuma chave
é incluída na imagem ou no `docker-compose.yml`.

### Cache e recursos

O volume `model_cache` preserva o cache do Hugging Face, Sentence Transformers e
Docling entre reinicializações. O primeiro uso de busca pode baixar o modelo de
embeddings; a primeira ingestão pode baixar modelos de layout e tabelas do
Docling. Reiniciar ou recriar containers não repete esses downloads enquanto o
volume for mantido.

A imagem é grande devido a PyTorch, Docling e Sentence Transformers. A resolução
atual do lock inclui também bibliotecas CUDA/NVIDIA e produziu uma imagem de cerca
de 9,6 GB no ambiente de validação, mesmo que o Compose não configure GPU. Em CPU,
a ingestão e a geração de embeddings podem ser lentas. Como referência inicial,
reserve pelo menos 4 GB de RAM; 8 GB ou mais é recomendado para ingestão de PDFs
maiores. Use `INGEST_DEVICE=cpu` para comportamento previsível ou prepare e teste
uma imagem/override CPU-only ou específica para o runtime da GPU.

### Atualização

Faça backup dos volumes e execute:

```bash
git pull
docker compose build --pull
docker compose up --detach --wait --remove-orphans
./scripts/container-smoke-test.sh
```

As atualizações da imagem não removem volumes. Antes de alterar o modelo de
embeddings, verifique a compatibilidade da coleção e planeje a reindexação.

### HTTPS com Caddy ou Nginx

Mantenha a porta `8501` vinculada ao loopback e coloque o proxy no mesmo host.
Exemplo mínimo de Caddyfile:

```caddyfile
chat.example.edu.br {
    reverse_proxy 127.0.0.1:8501
}
```

Exemplo de servidor Nginx, com WebSocket necessário ao Streamlit:

```nginx
server {
    listen 443 ssl http2;
    server_name chat.example.edu.br;
    client_max_body_size 30m;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

O gerenciamento dos certificados deve ser feito pelo Caddy, Certbot ou pela
infraestrutura institucional. Certificados e chaves reais não pertencem ao
repositório nem à imagem. O proxy também deve aplicar o limite de upload e as
políticas de acesso da instituição.

## Testes

```bash
uv run pytest
```

## Avaliação reproduzível

Os resultados de `evaluation/results/complete` pertencem à execução densa
histórica e não devem ser atribuídos ao BM25 atual. O executor faz um preflight da
configuração segura publicada por `/health` e interrompe a execução quando a API
diverge do arquivo congelado.

Com a API BM25 ativa, execute desenvolvimento em uma pasta nova:

```bash
uv run python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split development \
  --output evaluation/results/official_bm25/development_run.json
```

Depois de revisar exclusivamente o desenvolvimento, congele e execute o conjunto
final uma vez. A comparação BM25 no conjunto final existente é retrospectiva; uma
avaliação confirmatória rigorosa exige um novo conjunto ainda não observado.

```bash
uv run python -m evaluation.freeze_config
uv run python -m evaluation.run \
  --benchmark evaluation/benchmark/benchmark_approved.json \
  --split final --confirm-final \
  --output evaluation/results/official_bm25/final_run.json
uv run python -m evaluation.report \
  --run evaluation/results/official_bm25/final_run.json \
  --output-dir evaluation/results/official_bm25/final
```

Os relatórios incluem o ranking inicial do recuperador, o contexto final do RAG,
matriz de confusão, acurácia, precisão, recall, F1, baseline de sempre responder e
contagens de citações. Nenhuma dessas medidas comprova correção factual.

## Scraper

Com o grupo `scraper` instalado e o Chromium disponível:

```bash
uv run python scraper/tcc_ifbs_licenciatura_em_matematica.py
```

O scraper usa Chromium sem interface gráfica por padrão e salva os PDFs em
`pdfs_ifb/` quando executado a partir da raiz do projeto. Para acompanhar o
navegador visualmente, execute com `SCRAPER_HEADLESS=false`.
