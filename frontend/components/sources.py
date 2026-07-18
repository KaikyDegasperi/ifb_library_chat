"""Apresentação visual das fontes retornadas pelo RAG."""

from html import escape
from typing import Any

import streamlit as st


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        st.info("A resposta não utilizou fontes do acervo.")
        return

    st.markdown("#### Fontes utilizadas")
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
        similarity = f"{score * 100:.0f}%" if isinstance(score, (int, float)) else "—"

        st.markdown(
            f"""
            <div class="source-card">
                <div class="section-kicker">Fonte {index:02d}</div>
                <h4>{title}</h4>
                <p>{'Página ' + page if page else 'Página não informada'} · {chapter} · {similarity} de similaridade</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _page_label(start: Any, end: Any) -> str:
    if start is None:
        return ""
    if end is None or end == start:
        return str(start)
    return f"{start}–{end}"
