"""Apresentação visual das fontes retornadas pelo RAG."""

from html import escape
from typing import Any

import streamlit as st

from frontend.api_client import APIClient, APIClientError


def render_sources(
    sources: list[dict[str, Any]],
    client: APIClient | None = None,
    *,
    key_prefix: str = "sources",
) -> None:
    if not sources:
        st.info("A resposta não utilizou fontes do acervo.")
        return

    st.markdown("#### Fontes do contexto")
    for index, source in enumerate(sources, start=1):
        title = escape(
            str(
                source.get("title")
                or source.get("file_name")
                or "Título não identificado"
            )
        )
        page = _page_label(source.get("page_start"), source.get("page_end"))
        chapter = escape(str(source.get("section") or "Seção não informada"))
        score = source.get("score")
        relevance = f"{score:.3f}" if isinstance(score, (int, float)) else "—"

        st.markdown(
            f"""
            <div class="source-card">
                <div class="section-kicker">Fonte {index:02d}</div>
                <h4>{title}</h4>
                <p>{'Página ' + page if page else 'Página não informada'} · {chapter} · relevância {relevance}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if client is not None and source.get("document_id"):
            label = f"Abrir página {page}" if page else "Abrir documento"
            if st.button(
                label,
                icon=":material/menu_book:",
                key=(
                    f"{key_prefix}-preview-"
                    f"{source.get('chunk_id') or index}-{index}"
                ),
                width="content",
            ):
                _render_document_preview(client, source)


@st.dialog(
    "Prévia do TCC",
    width="large",
    icon=":material/menu_book:",
)
def _render_document_preview(
    client: APIClient,
    source: dict[str, Any],
) -> None:
    title = str(source.get("title") or source.get("file_name") or "TCC")
    page = _page_label(source.get("page_start"), source.get("page_end"))
    st.subheader(title)
    if page:
        st.caption(f"Trecho citado na página {page}.")
    if source.get("section"):
        st.caption(f"Seção: {source['section']}")
    try:
        pdf = client.get_document_pdf(str(source["document_id"]))
    except APIClientError as exc:
        st.error(f"Não foi possível abrir a prévia: {exc}")
        return
    st.pdf(pdf, height="stretch", key=f"pdf-preview-{source['document_id']}")


def _page_label(start: Any, end: Any) -> str:
    if start is None:
        return ""
    if end is None or end == start:
        return str(start)
    return f"{start}–{end}"
