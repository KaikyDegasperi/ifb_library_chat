"""Página administrativa do acervo."""

import os
import unicodedata
from typing import Any

import streamlit as st

from frontend.api_client import (
    APIClient,
    APIClientError,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
)


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

    section = st.segmented_control(
        "Seção de gerenciamento",
        ["Documentos", "Adicionar PDF", "Resumo"],
        default="Documentos",
        key="management-section",
        label_visibility="collapsed",
        width="stretch",
    )

    if section == "Adicionar PDF":
        _render_upload(client, documents or [])
    elif section == "Resumo":
        _render_summary(documents or [])
    else:
        _render_document_list(client, documents or [])


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


def _render_upload(client: APIClient, documents: list[dict[str, Any]]) -> None:
    st.subheader(":material/upload_file: Upload de novo PDF")
    maximum_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    uploaded = st.file_uploader(
        "Selecione um arquivo PDF",
        type=["pdf"],
        accept_multiple_files=False,
        help=f"Formato PDF, com tamanho máximo de {maximum_mb} MB.",
    )
    valid = True
    if uploaded is not None:
        if not uploaded.name.lower().endswith(".pdf"):
            st.error("Selecione um arquivo com extensão .pdf.")
            valid = False
        if uploaded.size > maximum_mb * 1024 * 1024:
            st.error(f"O arquivo excede o limite de {maximum_mb} MB.")
            valid = False
        if valid:
            st.caption(f"Arquivo selecionado: {uploaded.name} ({_size(uploaded.size)})")

    if not st.button(
        "Processar e indexar PDF",
        type="primary",
        disabled=uploaded is None or not valid,
        width="stretch",
    ):
        return

    existing_ids = {item.get("document_id") for item in documents}
    with st.status("Enviando o PDF para a FastAPI...", expanded=True) as status:
        try:
            result = client.ingest_document(
                uploaded.name,
                uploaded.getvalue(),
                uploaded.type or "application/pdf",
            )
        except APITimeoutError as exc:
            status.update(label="Tempo limite excedido", state="error")
            st.error(str(exc))
            return
        except APIUnavailableError as exc:
            status.update(label="FastAPI indisponível", state="error")
            st.error(str(exc))
            return
        except APIResponseError as exc:
            status.update(label="Falha na ingestão", state="error")
            if exc.status_code in {400, 413, 415, 422}:
                st.error(f"O PDF foi rejeitado: {exc}")
            else:
                st.error(f"Erro inesperado da API: {exc}")
            return
        except APIClientError as exc:
            status.update(label="Falha na ingestão", state="error")
            st.error(str(exc))
            return

        duplicate = result.get("document_id") in existing_ids
        status.update(
            label=(
                "Documento já existente verificado com sucesso"
                if duplicate
                else "Documento processado e indexado"
            ),
            state="complete",
        )
        st.success(
            f"{result.get('file_name', uploaded.name)} está disponível com "
            f"{result.get('chunk_count', 0)} chunks."
        )
    st.session_state.documents_refresh = True
    st.rerun()


def _render_document_list(client: APIClient, documents: list[dict[str, Any]]) -> None:
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
                    _delete(client, document_id)
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


def _delete(client: APIClient, document_id: str) -> None:
    try:
        result = client.delete_document(document_id)
    except APITimeoutError as exc:
        st.error(str(exc))
        return
    except APIClientError as exc:
        st.error(f"Não foi possível excluir o documento: {exc}")
        return
    st.session_state.delete_pending = None
    st.success(f"{result.get('deleted_chunks', 0)} chunks foram removidos.")
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
