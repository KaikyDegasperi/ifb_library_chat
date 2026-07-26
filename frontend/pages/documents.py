"""Página administrativa do acervo."""

import os
import unicodedata
from collections.abc import Callable, Sequence
from typing import Any, Protocol, TypedDict

import streamlit as st

from frontend.api_client import (
    APIClient,
    APIClientError,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
)

ADMIN_TOKEN_STATE_KEY = "admin_api_token"
ADMIN_AUTH_ERROR_STATE_KEY = "admin_auth_error"
UPLOAD_BATCH_RESULTS_STATE_KEY = "upload_batch_results"
UPLOAD_BATCH_KEY_STATE_KEY = "upload_batch_key"


class UploadedPDF(Protocol):
    """Contrato mínimo dos arquivos retornados pelo file uploader."""

    name: str
    size: int
    type: str | None

    def getvalue(self) -> bytes: ...


class BatchUploadResult(TypedDict):
    file_name: str
    status: str
    message: str
    chunk_count: int


def render_catalog_page(
    documents: list[dict[str, Any]] | None,
    api_available: bool,
) -> None:
    """Exibe o catálogo público sem controles administrativos."""
    st.markdown(
        """
        <div class="hero-card compact">
            <div class="section-kicker">Catálogo acadêmico</div>
            <h1>Explorar o acervo</h1>
            <p>Localize um trabalho e abra somente os detalhes que deseja consultar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not api_available:
        st.error(
            "O catálogo está temporariamente indisponível.",
            icon=":material/cloud_off:",
        )
        return

    available_documents = documents or []
    years = sorted(
        {str(item["year"]) for item in available_documents if item.get("year")},
        reverse=True,
    )
    search_column, year_column = st.columns([3, 1], vertical_alignment="bottom")
    with search_column:
        query = st.text_input(
            "Buscar no acervo",
            placeholder="Título, autor, orientador ou arquivo",
            icon=":material/search:",
            key="catalog-search",
        )
    with year_column:
        selected_year = st.selectbox(
            "Ano",
            ["Todos os anos", *years],
            key="catalog-year",
        )

    filtered_documents = _filter_documents(
        available_documents,
        query,
        None if selected_year == "Todos os anos" else selected_year,
    )
    st.caption(
        f"{len(filtered_documents)} de {len(available_documents)} "
        "trabalho(s) encontrado(s)."
    )

    if not available_documents:
        st.info("O acervo ainda não possui documentos indexados.")
        return
    if not filtered_documents:
        st.info("Nenhum trabalho corresponde aos filtros selecionados.")
        return

    for index, document in enumerate(filtered_documents):
        with st.expander(
            _document_label(document),
            icon=":material/article:",
            type="compact",
            key=f"catalog-document-{document.get('document_id') or index}",
        ):
            _render_public_details(document)


def render_documents_page(
    client: APIClient,
    documents: list[dict[str, Any]] | None,
    api_available: bool,
) -> None:
    st.markdown(
        """
        <div class="hero-card compact">
            <div class="section-kicker">Gerenciamento do acervo</div>
            <h1>Gestão institucional dos documentos</h1>
            <p>Publique, revise e atualize os documentos consultáveis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not api_available:
        st.error(
            "A FastAPI está indisponível. O gerenciamento foi desativado.",
            icon=":material/cloud_off:",
        )
        return

    admin_token = _admin_access()
    if admin_token is None:
        return

    section = st.segmented_control(
        "Seção de gerenciamento",
        ["Documentos", "Adicionar PDF", "Resumo"],
        default="Documentos",
        key="management-section",
        label_visibility="collapsed",
        width="stretch",
    )

    if section == "Adicionar PDF":
        _render_upload(client, admin_token)
    elif section == "Resumo":
        _render_summary(documents or [])
    else:
        _render_document_list(client, documents or [], admin_token)


def _admin_access() -> str | None:
    error = st.session_state.pop(ADMIN_AUTH_ERROR_STATE_KEY, None)
    if error:
        st.error(str(error), icon=":material/lock:")

    stored = st.session_state.get(ADMIN_TOKEN_STATE_KEY)
    if isinstance(stored, str) and stored:
        status, action = st.columns([4, 1], vertical_alignment="center")
        with status:
            st.success(
                "Credencial administrativa carregada somente nesta sessão.",
                icon=":material/verified_user:",
            )
        with action:
            if st.button(
                "Sair",
                icon=":material/logout:",
                width="stretch",
                key="admin-logout",
            ):
                st.session_state.pop(ADMIN_TOKEN_STATE_KEY, None)
                st.session_state.pop("delete_pending", None)
                st.rerun()
        return stored

    st.info(
        "Informe a credencial administrativa para enviar, reindexar ou excluir "
        "documentos. A consulta pública continua disponível sem autenticação.",
        icon=":material/admin_panel_settings:",
    )
    with st.form("admin-auth", clear_on_submit=True, border=True):
        entered = st.text_input(
            "Token administrativo",
            type="password",
            help="A credencial permanece somente nesta sessão do navegador.",
        )
        submitted = st.form_submit_button(
            "Acessar gerenciamento",
            type="primary",
            icon=":material/login:",
            width="stretch",
        )
    if submitted:
        token = entered.strip()
        if not token:
            st.warning("Informe o token administrativo.")
        else:
            st.session_state[ADMIN_TOKEN_STATE_KEY] = token
            st.rerun()
    return None


def _render_summary(documents: list[dict[str, Any]]) -> None:
    st.subheader(":material/monitoring: Resumo do acervo")
    summary = [
        ("Total de documentos", len(documents or [])),
        ("Indexados", len(documents or [])),
        ("Processando", 0),
        ("Com erro", 0),
    ]
    columns = st.columns(4)
    for column, (label, value) in zip(columns, summary):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="section-kicker">{label}</div>
                    <h2>{value}</h2>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_upload(
    client: APIClient,
    admin_token: str,
) -> None:
    st.subheader(":material/upload_file: Upload de PDFs em lote")
    maximum_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    st.caption(
        "Selecione vários arquivos. Eles serão processados um de cada vez "
        "e uma falha não interromperá os demais."
    )
    previous_results = st.session_state.get(UPLOAD_BATCH_RESULTS_STATE_KEY)
    if isinstance(previous_results, list) and previous_results:
        _render_batch_results(previous_results)

    upload_key = st.session_state.setdefault(UPLOAD_BATCH_KEY_STATE_KEY, 0)
    with st.container(border=True):
        uploaded_files = st.file_uploader(
            "Selecione os arquivos PDF",
            type=["pdf"],
            accept_multiple_files=True,
            max_upload_size=maximum_mb,
            help=f"Cada PDF pode ter no máximo {maximum_mb} MB.",
            key=f"document-upload-batch-{upload_key}",
        )
        valid_files, validation_errors = _validate_upload_batch(
            uploaded_files,
            maximum_mb * 1024 * 1024,
        )
        if uploaded_files:
            total_size = sum(uploaded.size for uploaded in uploaded_files)
            st.caption(
                f"{len(uploaded_files)} arquivo(s) selecionado(s) · "
                f"{_size(total_size)} no total"
            )
        for error in validation_errors:
            st.error(error, icon=":material/error:")
        submitted = st.button(
            (
                f"Processar e indexar {len(valid_files)} PDF(s)"
                if valid_files
                else "Selecione os PDFs"
            ),
            type="primary",
            icon=":material/play_arrow:",
            disabled=not valid_files,
            width="stretch",
        )

    if not submitted:
        return

    progress = st.progress(0, text="Preparando o lote...")
    with st.status("Processando o lote de PDFs...", expanded=True) as status:
        try:
            results = _process_upload_batch(
                client,
                valid_files,
                admin_token=admin_token,
                on_progress=lambda current, total, name: progress.progress(
                    current / total,
                    text=f"{current} de {total}: {name}",
                ),
            )
        except APIResponseError as exc:
            if exc.status_code in {401, 403}:
                _deny_admin_access()
            status.update(label="Não foi possível processar o lote", state="error")
            if exc.status_code == 503:
                st.error("As operações administrativas estão desabilitadas na API.")
            else:
                st.error(f"Erro inesperado da API: {exc}")
            return

        succeeded = sum(result["status"] == "success" for result in results)
        failed = len(results) - succeeded
        status.update(
            label=f"Lote concluído: {succeeded} sucesso(s), {failed} falha(s)",
            state="complete" if not failed else "error",
            expanded=bool(failed),
        )
    st.session_state[UPLOAD_BATCH_RESULTS_STATE_KEY] = results
    st.session_state[UPLOAD_BATCH_KEY_STATE_KEY] = upload_key + 1
    st.rerun()


def _validate_upload_batch(
    uploaded_files: Sequence[UploadedPDF],
    maximum_size_bytes: int,
) -> tuple[list[UploadedPDF], list[str]]:
    valid_files: list[UploadedPDF] = []
    errors: list[str] = []
    names: set[str] = set()
    for uploaded in uploaded_files:
        normalized_name = unicodedata.normalize("NFKC", uploaded.name).casefold()
        if not uploaded.name.lower().endswith(".pdf"):
            errors.append(f"{uploaded.name}: o arquivo precisa ter extensão .pdf.")
        elif uploaded.size > maximum_size_bytes:
            errors.append(
                f"{uploaded.name}: excede o limite de {_size(maximum_size_bytes)}."
            )
        elif normalized_name in names:
            errors.append(f"{uploaded.name}: nome repetido no lote.")
        else:
            valid_files.append(uploaded)
            names.add(normalized_name)
    return valid_files, errors


def _process_upload_batch(
    client: APIClient,
    uploaded_files: Sequence[UploadedPDF],
    *,
    admin_token: str,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[BatchUploadResult]:
    results: list[BatchUploadResult] = []
    total = len(uploaded_files)
    for current, uploaded in enumerate(uploaded_files, start=1):
        try:
            document = client.ingest_document(
                uploaded.name,
                uploaded.getvalue(),
                uploaded.type or "application/pdf",
                admin_token=admin_token,
            )
        except APIResponseError as exc:
            if exc.status_code in {401, 403, 503}:
                raise
            results.append(_failed_upload(uploaded.name, str(exc)))
        except (APITimeoutError, APIUnavailableError, APIClientError) as exc:
            results.append(_failed_upload(uploaded.name, str(exc)))
        else:
            chunk_count = int(document.get("chunk_count", 0))
            results.append(
                {
                    "file_name": str(document.get("file_name") or uploaded.name),
                    "status": "success",
                    "message": f"Indexado com {chunk_count} chunks.",
                    "chunk_count": chunk_count,
                }
            )
        if on_progress:
            on_progress(current, total, uploaded.name)
    return results


def _failed_upload(file_name: str, message: str) -> BatchUploadResult:
    return {
        "file_name": file_name,
        "status": "error",
        "message": message,
        "chunk_count": 0,
    }


def _render_batch_results(results: Sequence[BatchUploadResult]) -> None:
    succeeded = sum(result["status"] == "success" for result in results)
    failed = len(results) - succeeded
    if failed:
        st.warning(
            f"Último lote: {succeeded} processado(s) e {failed} com falha.",
            icon=":material/warning:",
        )
    else:
        st.success(
            f"Último lote: {succeeded} PDF(s) processado(s) com sucesso.",
            icon=":material/check_circle:",
        )
    for result in results:
        icon = (
            ":material/check_circle:"
            if result["status"] == "success"
            else ":material/error:"
        )
        st.write(f"{icon} **{result['file_name']}** — {result['message']}")


def _render_document_list(
    client: APIClient,
    documents: list[dict[str, Any]],
    admin_token: str,
) -> None:
    st.subheader(":material/library_books: Documentos indexados")
    if not documents:
        st.info("O acervo ainda não possui documentos indexados.")
        return

    st.caption(f"{len(documents)} documento(s) disponível(is).")
    for index, document in enumerate(documents):
        document_id = str(document.get("document_id", ""))
        title = document.get("title") or "Título não identificado"
        delete_pending = st.session_state.get("delete_pending") == document_id
        with st.expander(
            _document_label(document),
            expanded=delete_pending,
            icon=":material/description:",
            type="compact",
            key=f"manage-document-{document_id or index}",
        ):
            st.markdown(f"#### {title}")
            author = document.get("author")
            if author:
                st.markdown(f"**Autor(a):** {author}")
            academic_details = []
            if document.get("advisor"):
                academic_details.append(f"Orientação: {document['advisor']}")
            if document.get("coadvisor"):
                academic_details.append(f"Coorientação: {document['coadvisor']}")
            if document.get("year"):
                academic_details.append(f"Ano: {document['year']}")
            if academic_details:
                st.caption(" · ".join(academic_details))
            st.markdown(f"**Arquivo:** `{document.get('file_name', '')}`")
            pages = _page_count(document)
            chunks = document.get("chunk_count", 0)
            st.caption(
                f"{pages} página(s) · {chunks} chunks · "
                f"processado em {_date(document.get('processed_at'))}"
            )
            st.caption(f"Status: indexado · ID: {document_id}")

            if delete_pending:
                st.warning("Confirma a exclusão deste documento do índice vetorial?")
                confirm, cancel = st.columns(2)
                if confirm.button(
                    "Confirmar exclusão",
                    key=f"confirm-{document_id}",
                    type="primary",
                    width="stretch",
                ):
                    _delete(client, document_id, admin_token)
                if cancel.button(
                    "Cancelar",
                    key=f"cancel-{document_id}",
                    width="stretch",
                ):
                    st.session_state.delete_pending = None
                    st.rerun()
            elif st.button(
                "Excluir do acervo",
                key=f"delete-{document_id}",
                width="stretch",
            ):
                st.session_state.delete_pending = document_id
                st.rerun()


def _filter_documents(
    documents: list[dict[str, Any]],
    query: str,
    year: str | None,
) -> list[dict[str, Any]]:
    normalized_query = _normalize(query)
    searchable_fields = ("title", "author", "advisor", "coadvisor", "file_name")
    result = []
    for document in documents:
        if year and str(document.get("year", "")) != year:
            continue
        searchable_text = " ".join(str(document.get(field) or "") for field in searchable_fields)
        if normalized_query and normalized_query not in _normalize(searchable_text):
            continue
        result.append(document)
    return result


def _render_public_details(document: dict[str, Any]) -> None:
    st.markdown(f"#### {document.get('title') or 'Título não identificado'}")
    author = document.get("author") or "Autor não informado"
    st.markdown(f"**Autor(a):** {author}")

    details = []
    if document.get("advisor"):
        details.append(f"Orientação: {document['advisor']}")
    if document.get("coadvisor"):
        details.append(f"Coorientação: {document['coadvisor']}")
    if document.get("year"):
        details.append(f"Ano: {document['year']}")
    if details:
        st.write(" · ".join(details))

    pages = _page_count(document)
    public_metadata = []
    if pages:
        public_metadata.append(f"{pages} página(s)")
    if document.get("file_name"):
        public_metadata.append(f"Arquivo: {document['file_name']}")
    if public_metadata:
        st.caption(" · ".join(public_metadata))


def _document_label(document: dict[str, Any]) -> str:
    title = str(document.get("title") or "Título não identificado").strip()
    if len(title) > 105:
        title = f"{title[:102].rstrip()}…"
    metadata = [
        str(value)
        for value in (document.get("author"), document.get("year"))
        if value
    ]
    return f"{title} — {' · '.join(metadata)}" if metadata else title


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _delete(client: APIClient, document_id: str, admin_token: str) -> None:
    try:
        result = client.delete_document(document_id, admin_token=admin_token)
    except APITimeoutError as exc:
        st.error(str(exc))
        return
    except APIResponseError as exc:
        if exc.status_code in {401, 403}:
            _deny_admin_access()
        if exc.status_code == 503:
            st.error("As operações administrativas estão desabilitadas na API.")
        else:
            st.error(f"Não foi possível excluir o documento: {exc}")
        return
    except APIClientError as exc:
        st.error(f"Não foi possível excluir o documento: {exc}")
        return
    st.session_state.delete_pending = None
    st.success(f"{result.get('deleted_chunks', 0)} chunks foram removidos.")
    st.rerun()


def _deny_admin_access() -> None:
    st.session_state.pop(ADMIN_TOKEN_STATE_KEY, None)
    st.session_state.pop("delete_pending", None)
    st.session_state[ADMIN_AUTH_ERROR_STATE_KEY] = (
        "Acesso administrativo negado. Confira o token e tente novamente."
    )
    st.rerun()


def _page_count(document: dict[str, Any]) -> int:
    start = document.get("page_start")
    end = document.get("page_end")
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return end - start + 1
    return 0


def _date(value: Any) -> str:
    if not value:
        return "data não informada"
    return str(value).replace("T", " ").replace("Z", " UTC")


def _size(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"
