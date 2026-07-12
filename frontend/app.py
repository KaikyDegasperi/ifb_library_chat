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

st.set_page_config(
    page_title="IFB Library Chat",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --bg: #0b1220;
        --surface: #111827;
        --surface-2: #172033;
        --border: #374151;
        --text: #f8fafc;
        --muted: #cbd5e1;
        --primary: #10b981;
        --primary-strong: #059669;
        --warning: #f59e0b;
        --danger: #ef4444;
    }
    .stApp {
        background: linear-gradient(135deg, #0b1220 0%, #111827 100%);
        color: var(--text);
    }
    [data-testid="stSidebar"] {
        background: #0b1220;
        border-right: 1px solid var(--border);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero-card, .metric-card, .source-card, .admin-card {
        background: rgba(17, 24, 39, 0.95);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 1.2rem 1.3rem;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    }
    .hero-card { margin-bottom: 1.25rem; }
    .metric-card { min-height: 100px; }
    .source-card { margin-bottom: 0.8rem; }
    .section-kicker {
        color: var(--primary);
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    h1, h2, h3, h4, p, div, label {
        color: var(--text);
    }
    .stTextArea textarea, .stTextInput input {
        border-radius: 16px !important;
        border: 1px solid var(--border) !important;
        background: var(--surface-2) !important;
        color: var(--text) !important;
    }
    .stButton>button, .stDownloadButton>button {
        border-radius: 999px !important;
        border: none !important;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-strong) 100%) !important;
        color: white !important;
        font-weight: 600 !important;
    }
    .stButton>button:hover {
        filter: brightness(1.05);
    }
    .stRadio > div {
        gap: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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

    with st.sidebar:
        st.markdown("### IFB")
        st.markdown("#### Library Chat")
        st.caption("Biblioteca digital do IFB")
        st.divider()

        selected_view = st.radio(
            "Navegação",
            ["Consulta", "Sobre o projeto"],
            label_visibility="collapsed",
            horizontal=False,
        )
        st.session_state.active_view = selected_view

        st.divider()
        if st.button("Acesso institucional", use_container_width=True):
            st.session_state.active_view = "Gerenciamento do acervo"
        if st.session_state.active_view == "Gerenciamento do acervo":
            if st.button("Voltar à consulta", use_container_width=True):
                st.session_state.active_view = "Consulta"

        st.caption("Licenciatura em Matemática · IFB Campus Estrutural")

    if st.session_state.active_view == "Consulta":
        render_chat_page(client, documents, api_available)
    elif st.session_state.active_view == "Gerenciamento do acervo":
        render_documents_page(client, documents, api_available)
    else:
        _render_about_page()


def _render_about_page() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="section-kicker">Sobre o projeto</div>
            <h1>Consulta inteligente ao acervo de TCCs</h1>
            <p>Esta experiência foi concebida para apresentar o acervo acadêmico com linguagem simples, confiança institucional e foco na pesquisa.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "O acesso público é orientado à consulta. O gerenciamento do acervo fica reservado à equipe institucional."
    )


if __name__ == "__main__":
    main()
