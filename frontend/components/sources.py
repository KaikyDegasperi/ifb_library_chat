"""Apresentação compacta das fontes retornadas pelo RAG."""

from typing import Any

import streamlit as st


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        st.info("A resposta não utilizou fontes do acervo.")
        return

    st.markdown("#### Fontes utilizadas")
    for index, source in enumerate(sources, start=1):
        title = source.get("title") or "Título não identificado"
        file_name = source.get("file_name") or "Arquivo não identificado"
        page = _page_label(source.get("page_start"), source.get("page_end"))
        with st.expander(f"Fonte {index} — {title}"):
            st.markdown(f"**Arquivo:** `{file_name}`")
            if page:
                st.markdown(f"**Página(s):** {page}")
            if source.get("section"):
                st.markdown(f"**Seção:** {source['section']}")
            score = source.get("score")
            if isinstance(score, (int, float)):
                st.markdown(f"**Similaridade:** {score:.3f}")
            if source.get("document_id"):
                st.caption(f"Documento: {source['document_id']}")


def _page_label(start: Any, end: Any) -> str:
    if start is None:
        return ""
    if end is None or end == start:
        return str(start)
    return f"{start}–{end}"
