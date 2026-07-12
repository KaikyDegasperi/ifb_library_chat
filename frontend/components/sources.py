"""Apresentação visual das fontes retornadas pelo RAG."""

from typing import Any

import streamlit as st


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        st.info("A resposta não utilizou fontes do acervo.")
        return

    st.markdown("#### Fontes utilizadas")
    for source in sources:
        title = source.get("title") or "Título não identificado"
        author = source.get("author") or "Autor não identificado"
        year = source.get("year") or "Ano não informado"
        page = _page_label(source.get("page_start"), source.get("page_end"))
        chapter = source.get("section") or "Seção não informada"
        score = source.get("score")
        similarity = f"{score:.3f}" if isinstance(score, (int, float)) else "—"

        st.markdown(
            f"""
            <div class="source-card">
                <h4>{title}</h4>
                <p><strong>Autor:</strong> {author}</p>
                <p><strong>Ano:</strong> {year}</p>
                <p><strong>Página:</strong> {page or 'Não informada'}</p>
                <p><strong>Capítulo:</strong> {chapter}</p>
                <p><strong>Similaridade:</strong> {similarity}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("Ver documento", use_container_width=True, disabled=True)


def _page_label(start: Any, end: Any) -> str:
    if start is None:
        return ""
    if end is None or end == start:
        return str(start)
    return f"{start}–{end}"
