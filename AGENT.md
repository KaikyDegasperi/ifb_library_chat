# AGENTS.md

## 1. Objetivo do projeto

Este projeto é um chatbot RAG para consulta aos Trabalhos de Conclusão de Curso
da Licenciatura em Matemática do IFB Campus Estrutural.

O sistema permite:

- enviar documentos PDF;
- processar PDFs com Docling;
- dividir documentos em chunks;
- gerar embeddings;
- indexar os chunks no ChromaDB;
- realizar busca semântica;
- gerar respostas com contexto usando um LLM;
- exibir as fontes usadas na resposta;
- administrar documentos por uma interface Streamlit.

---

## 2. Stack principal

- Python 3.14
- FastAPI
- Streamlit
- Docling
- ChromaDB
- sentence-transformers
- Pydantic Settings
- httpx
- pytest
- uv

---

## 3. Arquitetura geral

O frontend não acessa diretamente os serviços internos.

Fluxo correto:

```text
Navegador
    ↓
Streamlit
    ↓ HTTP
FastAPI
    ↓
Rotas
    ↓
Serviços
    ↓
Ingestão, ChromaDB e RAG

O frontend deve sempre chamar a API usando frontend/api_client.py.

Não importar diretamente no frontend:

Docling;
ChromaDB;
serviços de ingestão;
serviços RAG;
repositórios;
modelo de embeddings.
4. Estrutura do projeto
Aplicação principal
app/api.py: criação e configuração principal da aplicação FastAPI.
app/main.py: alias da aplicação para inicialização.
app/config.py: configurações carregadas por variáveis de ambiente.
app/dependencies.py: construção e injeção de dependências.
app/health.py: verificações de saúde dos componentes.
app/logging_config.py: configuração de logs.
Rotas HTTP
app/routes/health.py: health check.
app/routes/documents.py: upload, ingestão, listagem e exclusão.
app/routes/search.py: busca semântica sem geração.
app/routes/chat.py: perguntas e respostas usando RAG.
app/routes/errors.py: respostas de erro padronizadas.

Rotas devem ser finas.

Rotas devem:

validar entrada;
chamar serviços;
converter resultados para schemas;
retornar respostas HTTP.

Rotas não devem conter regras de negócio complexas.

Schemas
app/schemas/chat.py
app/schemas/common.py
app/schemas/documents.py
app/schemas/health.py
app/schemas/search.py

Schemas definem os contratos públicos da API.

Ao alterar um contrato:

atualize o schema;
atualize a rota;
atualize o cliente HTTP;
atualize os testes;
verifique compatibilidade com o frontend.
Serviços
app/services/documents.py: regras de negócio de documentos.
app/ingestion/service.py: processamento dos PDFs.
app/vectorstore/service.py: indexação e busca vetorial.
app/rag/service.py: orquestração da resposta RAG.

As regras de negócio devem permanecer nos serviços, não nas rotas.

Repositórios
app/repositories/documents.py: persistência e leitura dos documentos.
app/repositories/models.py: modelos usados pela persistência.

O acesso a dados deve passar pelos repositórios quando houver uma abstração
existente para isso.

Ingestão
app/ingestion/service.py: processamento com Docling.
app/ingestion/chunking.py: divisão do documento em chunks.
app/ingestion/models.py: modelos da ingestão.

Fluxo esperado:

PDF
    ↓
Docling
    ↓
Documento estruturado
    ↓
Chunks com metadados
    ↓
Arquivos em data/processed

O chunker deve preservar, quando possível:

título;
seção;
página;
ordem original;
identificação do documento.

Não misturar conteúdo de seções diferentes apenas para preencher o tamanho do
chunk.

Banco vetorial
app/vectorstore/embeddings.py: carregamento e geração de embeddings.
app/vectorstore/service.py: indexação e busca no ChromaDB.
app/vectorstore/models.py: modelos dos resultados vetoriais.

O ChromaDB deve permanecer persistente em data/chroma.

Não alterar o modelo de embeddings sem verificar:

dimensão dos vetores;
necessidade de recriar a coleção;
impacto nos documentos já indexados;
impacto nos testes.
RAG
app/rag/service.py: fluxo principal do RAG.
app/rag/llm.py: comunicação com o provedor de LLM.
app/rag/factory.py: construção do provedor.
app/rag/prompts.py: prompts do sistema.
app/rag/models.py: modelos internos.
app/rag/exceptions.py: falhas controladas.

Fluxo esperado:

Pergunta
    ↓
Busca vetorial
    ↓
Filtro por similaridade
    ↓
Remoção de resultados duplicados
    ↓
Limitação do contexto
    ↓
Construção do prompt
    ↓
LLM
    ↓
Resposta com fontes

A resposta não deve inventar informações que não estejam nos documentos
recuperados.

Quando não houver contexto suficiente, o sistema deve informar que não
encontrou resposta no acervo.

Frontend
frontend/app.py: entrada da interface Streamlit.
frontend/api_client.py: chamadas HTTP para a FastAPI.
frontend/pages/chat.py: consulta ao acervo.
frontend/pages/documents.py: administração de documentos.
frontend/components/sources.py: apresentação das fontes.

O frontend deve permanecer uma camada de apresentação.

Não colocar nele regras de ingestão, busca vetorial ou geração de respostas.

5. Regras de implementação

Ao alterar o código:

preserve a arquitetura existente;
faça a menor alteração necessária;
não reescreva arquivos inteiros sem necessidade;
não crie abstrações sem uso real;
não adicione dependências sem justificar;
não invente funções, classes, endpoints ou arquivos;
verifique os nomes reais antes de referenciá-los;
use type hints;
use nomes em inglês no código;
mensagens exibidas ao usuário podem estar em português;
mantenha tratamento explícito de erros;
mantenha compatibilidade com Python 3.14;
não exponha segredos;
nunca coloque chaves reais no repositório;
não altere .env.example com credenciais;
mantenha o frontend desacoplado do backend.
6. Segurança de documentos

No upload de PDFs, preservar as validações existentes:

aceitar apenas arquivos PDF;
validar extensão;
validar MIME type;
validar assinatura %PDF-;
bloquear nomes de arquivo inseguros;
bloquear caminhos absolutos;
impedir saída de DOCUMENTS_DIR;
respeitar o tamanho máximo configurado;
não sobrescrever arquivos de forma insegura.

Não remover validações de segurança para simplificar uma implementação.

7. Configurações importantes

As configurações devem continuar vindo de variáveis de ambiente.

Principais variáveis:

APP_NAME
APP_ENV
LOG_LEVEL
MAX_UPLOAD_SIZE_MB

DOCUMENTS_DIR
PROCESSED_DIR
INGEST_CHUNK_SIZE
INGEST_CHUNK_OVERLAP
INGEST_DEVICE

CHROMA_DIR
CHROMA_COLLECTION

EMBEDDING_MODEL
EMBEDDING_BATCH_SIZE
SEARCH_TOP_K

LLM_PROVIDER
LLM_BASE_URL
LLM_MODEL
LLM_API_KEY
LLM_TIMEOUT_SECONDS

RAG_RETRIEVAL_TOP_K
RAG_MIN_SIMILARITY
RAG_MAX_CONTEXT_CHARS
RAG_MAX_QUESTION_CHARS
RAG_DUPLICATE_THRESHOLD

Não criar valores de configuração espalhados pelo código quando eles já podem
ser definidos em app/config.py.

8. Uso com Ollama

Para usar um modelo local compatível com a API OpenAI:

LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=qwen2.5-coder:3b
LLM_API_KEY=ollama
LLM_TIMEOUT_SECONDS=60

O modelo usado pelo chatbot do acervo e o modelo usado pelo assistente do VS
Code são usos separados, mesmo que ambos sejam servidos pelo Ollama.

9. Testes

Antes de alterar uma funcionalidade, procure o teste relacionado.

Arquivos principais:

tests/test_api.py
tests/test_chunking.py
tests/test_config.py
tests/test_frontend_api_client.py
tests/test_health.py
tests/test_ingestion.py
tests/test_rag.py
tests/test_vectorstore.py

Toda correção de bug deve, quando possível, incluir um teste que falhe antes da
correção e passe depois.

Comando para executar todos os testes:

uv run pytest

Comando para executar um arquivo específico:

uv run pytest tests/test_rag.py

Comando para executar um teste específico:

uv run pytest tests/test_rag.py::nome_do_teste

Não considerar a tarefa concluída sem informar como ela foi validada.

10. Execução local

Instalar dependências:

uv sync
cp .env.example .env

Iniciar a API:

uv run uvicorn app.main:app --reload

Iniciar o frontend em outro terminal:

API_BASE_URL=http://127.0.0.1:8000 \
uv run streamlit run frontend/app.py

API:

http://127.0.0.1:8000

Documentação Swagger:

http://127.0.0.1:8000/docs

Frontend:

http://127.0.0.1:8501
11. Comandos da pipeline

Ingerir documentos:

uv run python -m app.cli.ingest

Indexar documentos processados:

uv run python -m app.cli.index

Executar busca pelo terminal:

uv run python -m app.cli.search "consulta desejada"

Antes de modificar esses comandos, verificar os argumentos reais definidos nos
respectivos módulos em app/cli.

12. Procedimento obrigatório para agentes

Antes de escrever código:

Leia este arquivo.
Leia o README.md.
Identifique o módulo envolvido.
Leia somente os arquivos relacionados à tarefa.
Leia os testes relacionados.
Explique resumidamente o fluxo atual.
Liste os arquivos que pretende alterar.
Proponha a menor mudança possível.
Aguarde aprovação quando a tarefa for ampla ou ambígua.

Durante a implementação:

Altere apenas os arquivos necessários.
Preserve contratos existentes.
Não faça refatorações paralelas.
Não adicione dependências sem necessidade.
Crie ou atualize testes.
Mantenha mensagens de erro compreensíveis.

Após a implementação:

Mostre um resumo das alterações.
Informe os arquivos modificados.
Informe os testes executados.
Informe qualquer teste que não tenha sido executado.
Aponte riscos ou limitações restantes.
Não declare que algo funciona sem ter validado.
13. Estratégia para modelos pequenos

Este repositório pode ser trabalhado com modelos locais pequenos.

Para economizar contexto:

leia primeiro este arquivo;
trabalhe em uma funcionalidade por vez;
use entre dois e cinco arquivos por tarefa;
não carregue o repositório inteiro;
prefira diffs pequenos;
não peça mudanças simultâneas em frontend, ingestão, RAG e infraestrutura;
execute testes específicos antes da suíte completa.

Exemplos de grupos de contexto:

Alteração no chat
AGENTS.md
app/routes/chat.py
app/schemas/chat.py
app/rag/service.py
tests/test_rag.py
Alteração na busca
AGENTS.md
app/routes/search.py
app/schemas/search.py
app/vectorstore/service.py
tests/test_vectorstore.py
Alteração na ingestão
AGENTS.md
app/ingestion/service.py
app/ingestion/chunking.py
app/ingestion/models.py
tests/test_ingestion.py
tests/test_chunking.py
Alteração no gerenciamento de documentos
AGENTS.md
app/routes/documents.py
app/services/documents.py
app/repositories/documents.py
app/schemas/documents.py
tests/test_api.py
Alteração no frontend
AGENTS.md
frontend/app.py
frontend/api_client.py
frontend/pages/chat.py
frontend/pages/documents.py
frontend/components/sources.py
tests/test_frontend_api_client.py
14. Formato esperado de resposta do agente

Para tarefas de análise, responder nesta ordem:

1. Entendimento da tarefa
2. Fluxo atual
3. Arquivos envolvidos
4. Problema identificado
5. Menor solução recomendada
6. Forma de validação

Para tarefas de implementação, responder nesta ordem:

1. Resumo da alteração
2. Arquivos alterados
3. Decisões técnicas
4. Testes adicionados ou modificados
5. Comandos de validação
6. Limitações ou riscos
15. Restrições

Não fazer sem solicitação explícita:

trocar FastAPI;
trocar Streamlit;
trocar Docling;
trocar ChromaDB;
trocar o modelo de embeddings;
alterar todos os contratos da API;
migrar o projeto para outra arquitetura;
adicionar autenticação complexa;
adicionar Redis, Celery ou Kubernetes;
transformar uma tarefa pequena em uma grande refatoração;
excluir testes existentes;
desabilitar validações para fazer testes passarem;
colocar regras de negócio no frontend.