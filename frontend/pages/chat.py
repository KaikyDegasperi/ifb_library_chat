"""Página pública de consulta ao acervo."""

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
    count = len(documents or [])
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("selected_source", None)

    status_class = "chat-status-dot" if api_available else "chat-status-dot offline"
    status_text = "Acervo conectado" if api_available else "Acervo indisponível"
    suggested_question: str | None = None

    with st.container(border=True, key="chat_window"):
        st.markdown(
            f"""
            <div class="chat-window-header">
                <div class="chat-window-identity">
                    <div class="chat-window-mark">✦</div>
                    <div>
                        <strong>Assistente do acervo</strong>
                        <small>TCCs da Licenciatura em Matemática</small>
                    </div>
                </div>
                <div class="chat-window-status">
                    <span class="{status_class}"></span>{status_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        history = st.container(
            height=520,
            border=False,
            key="chat_history",
            autoscroll=True,
        )
        with history:
            if not api_available:
                st.warning(
                    "A consulta está temporariamente indisponível. Verifique o backend.",
                    icon=":material/cloud_off:",
                )
            elif not documents:
                st.info(
                    "O acervo ainda não possui documentos indexados.",
                    icon=":material/library_books:",
                )

            if not st.session_state.chat_messages:
                st.markdown(
                    f"""
                    <section class="welcome-shell isolated">
                        <div class="ai-mark">✦</div>
                        <div class="eyebrow">Assistente de pesquisa</div>
                        <h1>O que você quer descobrir no acervo?</h1>
                        <p class="intro">Faça perguntas aos TCCs de Matemática. As respostas são acompanhadas das fontes recuperadas.</p>
                        <div class="collection-badge">● {count} TCCs indexados</div>
                    </section>
                    """,
                    unsafe_allow_html=True,
                )
                suggestions = [
                    "Quais metodologias ativas aparecem nos TCCs?",
                    "Encontre pesquisas sobre educação inclusiva",
                    "Como os jogos são usados no ensino de matemática?",
                ]
                selected = st.pills(
                    "Perguntas sugeridas",
                    suggestions,
                    label_visibility="collapsed",
                    key="chat_suggestions",
                )
                if selected:
                    suggested_question = selected
            else:
                _render_messages(client)

        question = st.chat_input(
            "Pergunte sobre os TCCs do acervo...",
            key="isolated_chat_input",
            disabled=not api_available or not documents,
            submit_mode="disable",
        )
        st.caption(
            "As respostas são geradas a partir dos documentos do acervo. "
            "Confira sempre as fontes."
        )

    prompt = suggested_question or question
    if prompt and prompt.strip():
        _submit_question(client, prompt.strip(), history)


def _render_messages(client: APIClient) -> None:
    for message_index, message in enumerate(st.session_state.chat_messages):
        if message["role"] == "user":
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar=":material/auto_awesome:"):
                st.caption("RESPOSTA FUNDAMENTADA NO ACERVO")
                st.markdown(message["content"])
                if message.get("sources"):
                    render_sources(
                        message.get("sources", []),
                        client,
                        key_prefix=f"message-{message_index}",
                    )
                _render_times(message)


def _submit_question(client: APIClient, question: str, history: Any) -> None:
    recent = st.session_state.setdefault("recent_questions", [])
    if question not in recent:
        recent.insert(0, question)
    st.session_state.chat_messages.append({"role": "user", "content": question})
    with history:
        with st.spinner("Consultando o acervo e montando a resposta..."):
            try:
                payload = client.chat(question, assistive_query_handling=True)
            except APITimeoutError as exc:
                _store_error(str(exc), "timeout")
                st.rerun()
            except APIUnavailableError as exc:
                _store_error(str(exc), "api")
                st.rerun()
            except APIResponseError as exc:
                _store_error(f"A API não conseguiu responder: {exc}", "api")
                st.rerun()
            except APIClientError as exc:
                _store_error(str(exc), "api")
                st.rerun()

        answer = str(payload.get("answer") or "").strip()
        sources = payload.get("sources") or []
        if not answer:
            answer = "A API não retornou uma resposta para esta pergunta."

        if sources:
            st.session_state.selected_source = sources[0]
        message = {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_time_ms": payload.get("retrieval_time_ms", 0),
            "generation_time_ms": payload.get("generation_time_ms", 0),
        }
        st.session_state.chat_messages.append(message)
    st.rerun()


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
