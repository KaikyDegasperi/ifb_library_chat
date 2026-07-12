"""Página administrativa do acervo."""

import os
from typing import Any

import streamlit as st

from frontend.api_client import (
    APIClient,
    APIClientError,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
)


def render_documents_page(
    client: APIClient,
    documents: list[dict[str, Any]] | None,
    api_available: bool,
) -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="section-kicker">Gerenciamento do acervo</div>
            <h1>Gestão institucional dos documentos</h1>
            <p>Esta área é reservada à equipe responsável por publicar, revisar e atualizar o acervo consultável.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not api_available:
        st.error("A FastAPI está indisponível. O gerenciamento foi desativado.")
        return

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

    st.divider()
    _render_upload(client, documents or [])
    st.divider()
    _render_document_list(client, documents or [])


def _render_upload(client: APIClient, documents: list[dict[str, Any]]) -> None:
    st.subheader("Upload de novo PDF")
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
        use_container_width=True,
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
    st.subheader("Documentos indexados")
    if not documents:
        st.info("O acervo ainda não possui documentos indexados.")
        return

    st.caption(f"{len(documents)} documento(s) disponível(is).")
    for document in documents:
        document_id = str(document.get("document_id", ""))
        title = document.get("title") or "Título não identificado"
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.markdown(f"**Arquivo:** `{document.get('file_name', '')}`")
            pages = _page_count(document)
            chunks = document.get("chunk_count", 0)
            st.caption(
                f"{pages} página(s) · {chunks} chunks · "
                f"processado em {_date(document.get('processed_at'))}"
            )
            st.caption(f"Status: indexado · ID: {document_id}")

            if st.session_state.get("delete_pending") == document_id:
                st.warning("Confirma a exclusão deste documento do índice vetorial?")
                confirm, cancel = st.columns(2)
                if confirm.button(
                    "Confirmar exclusão",
                    key=f"confirm-{document_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    _delete(client, document_id)
                if cancel.button(
                    "Cancelar",
                    key=f"cancel-{document_id}",
                    use_container_width=True,
                ):
                    st.session_state.delete_pending = None
                    st.rerun()
            elif st.button(
                "Excluir do acervo",
                key=f"delete-{document_id}",
                use_container_width=True,
            ):
                st.session_state.delete_pending = document_id
                st.rerun()


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
