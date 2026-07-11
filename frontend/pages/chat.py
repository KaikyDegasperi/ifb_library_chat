"""Página de conversa com o acervo."""

from typing import Any

import streamlit as st

from frontend.api_client import (
    APIClient,
    APIClientError,
    APIResponseError,
    APITimeoutError,
    APIUnavailableError,
)
from frontend.components.sources import render_sources


def render_chat_page(
    client: APIClient,
    documents: list[dict[str, Any]] | None,
    api_available: bool,
) -> None:
    st.title("Chatbot dos TCCs de Matemática do IFB")
    st.write(
        "Consulte os Trabalhos de Conclusão de Curso da Licenciatura em "
        "Matemática do IFB Campus Estrutural. As respostas são produzidas a "
        "partir dos trechos recuperados e apresentam suas fontes."
    )

    count = len(documents or [])
    status_column, count_column = st.columns(2)
    status_column.metric("Estado da API", "Disponível" if api_available else "Indisponível")
    count_column.metric("Documentos indexados", count)

    if not api_available:
        st.error(
            "A FastAPI está indisponível. Inicie o backend e atualize esta página."
        )
    elif not documents:
        st.warning(
            "O acervo está vazio. Envie um TCC na página Gerenciar documentos "
            "antes de fazer perguntas."
        )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources", []))
                _render_times(message)

    top_k = st.select_slider(
        "Quantidade máxima de fontes",
        options=[3, 5, 8, 10],
        value=5,
        help="Define quantos trechos candidatos serão recuperados.",
    )
    question = st.chat_input(
        "Digite sua pergunta sobre os TCCs",
        disabled=not api_available or not documents,
    )
    if question is None:
        return
    if not question.strip():
        st.warning("Digite uma pergunta antes de enviar.")
        return

    st.session_state.chat_messages.append(
        {"role": "user", "content": question.strip()}
    )
    with st.chat_message("user"):
        st.markdown(question.strip())

    with st.chat_message("assistant"):
        with st.spinner("Consultando os TCCs e gerando a resposta..."):
            try:
                payload = client.chat(question.strip(), top_k=top_k)
            except APITimeoutError as exc:
                _store_error(str(exc), "timeout")
                st.error(str(exc))
                return
            except APIUnavailableError as exc:
                _store_error(str(exc), "api")
                st.error(str(exc))
                return
            except APIResponseError as exc:
                _store_error(str(exc), "api")
                st.error(f"A API não conseguiu responder: {exc}")
                return
            except APIClientError as exc:
                _store_error(str(exc), "api")
                st.error(str(exc))
                return

        answer = str(payload.get("answer") or "").strip()
        sources = payload.get("sources") or []
        if not answer:
            answer = "A API não retornou uma resposta para esta pergunta."
            st.warning(answer)
        elif not sources:
            st.warning(answer)
        elif "não foi possível gerar" in answer.lower():
            st.error(answer)
        else:
            st.markdown(answer)
        render_sources(sources)
        message = {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_time_ms": payload.get("retrieval_time_ms", 0),
            "generation_time_ms": payload.get("generation_time_ms", 0),
        }
        st.session_state.chat_messages.append(message)
        _render_times(message)


def _store_error(message: str, kind: str) -> None:
    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": message,
            "sources": [],
            "error_kind": kind,
        }
    )


def _render_times(message: dict[str, Any]) -> None:
    retrieval = message.get("retrieval_time_ms")
    generation = message.get("generation_time_ms")
    if retrieval is not None and generation is not None:
        st.caption(f"Recuperação: {retrieval} ms · Geração: {generation} ms")
