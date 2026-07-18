"""Ponto de entrada da interface Streamlit."""

import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.api_client import APIClient, APIClientError
from frontend.pages.chat import render_chat_page
from frontend.pages.documents import render_documents_page
from frontend.styles import apply_styles

st.set_page_config(
    page_title="Biblioteca IFB · Assistente de pesquisa",
    page_icon=":material/local_library:",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles()


@st.cache_resource
def get_api_client() -> APIClient:
    return APIClient()


def load_backend_state(client: APIClient) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    try:
        return client.health(), client.list_documents()
    except APIClientError:
        return None, None


def main() -> None:
    client = get_api_client()
    health, documents = load_backend_state(client)
    api_available = health is not None

    if "active_view" not in st.session_state:
        st.session_state.active_view = "Consulta"
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "recent_questions" not in st.session_state:
        st.session_state.recent_questions = []

    with st.sidebar:
        st.markdown(
            """
            <div class="ifb-brand">
                <div class="ifb-brand-mark">IF</div>
                <div class="ifb-brand-copy">
                    <strong>Biblioteca IFB</strong>
                    <small>Campus Estrutural</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Nova conversa",
            icon=":material/add:",
            type="primary",
            width="stretch",
        ):
            st.session_state.chat_messages = []
            st.session_state.selected_source = None
            st.session_state.active_view = "Consulta"

        history_filter = st.text_input(
            "Buscar conversas",
            placeholder="Buscar conversas",
            label_visibility="collapsed",
            icon=":material/search:",
        )

        st.markdown('<div class="sidebar-label">Navegação</div>', unsafe_allow_html=True)
        if st.button("Conversas", icon=":material/chat:", width="stretch"):
            st.session_state.active_view = "Consulta"
        if st.button("Explorar acervo", icon=":material/library_books:", width="stretch"):
            st.session_state.active_view = "Gerenciamento do acervo"
        if st.button("Sobre o projeto", icon=":material/info:", width="stretch"):
            st.session_state.active_view = "Sobre o projeto"

        recent = [
            item
            for item in st.session_state.recent_questions
            if history_filter.casefold() in item.casefold()
        ]
        if recent:
            st.markdown('<div class="sidebar-label">Recentes</div>', unsafe_allow_html=True)
            for item in recent[:6]:
                st.markdown(
                    f'<div class="history-item">{_escape(item)}</div>',
                    unsafe_allow_html=True,
                )

        st.space("small")
        if st.button(
            "Gerenciar acervo",
            icon=":material/settings:",
            width="stretch",
            help="Acesso institucional",
        ):
            st.session_state.active_view = "Gerenciamento do acervo"

        st.markdown(
            """
            <div class="ifb-profile">
                <span>IF</span>
                <div><strong>Acervo de Matemática</strong><small>Licenciatura · IFB</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.active_view == "Consulta":
        render_chat_page(client, documents, api_available)
    else:
        status_class = "status-dot" if api_available else "status-dot offline"
        status_text = "Acervo conectado" if api_available else "Acervo indisponível"
        st.markdown(
            f'<div class="status-bar"><span class="{status_class}"></span>{status_text}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.active_view == "Gerenciamento do acervo":
            render_documents_page(client, documents, api_available)
        else:
            _render_about_page()


def _render_about_page() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="section-kicker">Sobre o projeto</div>
            <h1>Pesquisa acadêmica com fontes verificáveis</h1>
            <p>O assistente conecta estudantes e pesquisadores aos TCCs da Licenciatura em Matemática do IFB Campus Estrutural.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    first, second = st.columns(2, gap="large")
    with first.container(border=True, height="stretch"):
        st.subheader(":material/auto_awesome: Como funciona")
        st.write(
            "As perguntas são comparadas aos trechos indexados do acervo. "
            "O modelo recebe somente o contexto recuperado para elaborar a resposta."
        )
    with second.container(border=True, height="stretch"):
        st.subheader(":material/fact_check: Compromisso com as fontes")
        st.write(
            "Cada resposta apresenta os trabalhos, páginas e seções usados. "
            "Consulte o documento original antes de usar a informação academicamente."
        )


def _escape(value: str) -> str:
    from html import escape

    return escape(value)


if __name__ == "__main__":
    main()
