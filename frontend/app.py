"""Ponto de entrada da interface Streamlit."""

from typing import Any

import streamlit as st

from frontend.api_client import APIClient, APIClientError
from frontend.pages.chat import render_chat_page
from frontend.pages.documents import render_documents_page

st.set_page_config(
    page_title="Chatbot dos TCCs do IFB",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
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

    st.sidebar.title("IFB Library Chat")
    st.sidebar.caption("Demonstração acadêmica de recuperação e geração")
    if api_available:
        status = health.get("status", "desconhecido")
        st.sidebar.success(f"FastAPI: {status}")
    else:
        st.sidebar.error("FastAPI indisponível")

    page = st.sidebar.radio(
        "Navegação",
        ["Consultar acervo", "Gerenciar documentos"],
    )
    st.sidebar.divider()
    st.sidebar.caption("Licenciatura em Matemática · IFB Campus Estrutural")

    if page == "Consultar acervo":
        render_chat_page(client, documents, api_available)
    else:
        render_documents_page(client, documents, api_available)


if __name__ == "__main__":
    main()
