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

    st.markdown(
        """
        <div class="hero-card">
            <div class="section-kicker">Consulta ao acervo</div>
            <h1>Chatbot dos TCCs da Licenciatura em Matemática</h1>
            <p>Consulte o acervo de Trabalhos de Conclusão de Curso com linguagem natural, recuperação semântica e fontes claras.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_column, count_column = st.columns([2, 1], gap="large")
    with summary_column:
        st.markdown(
            """
            <div class="metric-card">
                <div class="section-kicker">Acervo disponível</div>
                <h2>Consulte o catálogo acadêmico com confiança</h2>
                <p>As respostas são fundamentadas em trechos recuperados dos TCCs indexados e acompanhadas de fontes.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with count_column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="section-kicker">TCCs indexados</div>
                <h2>{count} disponíveis</h2>
                <p>Volume consultável do acervo institucional.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not api_available:
        st.warning("A consulta está temporariamente indisponível. Verifique o backend antes de continuar.")
    elif not documents:
        st.info("O acervo ainda não possui documentos indexados. A equipe pode complementar o catálogo em breve.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "selected_source" not in st.session_state:
        st.session_state.selected_source = None

    left_column, right_column = st.columns([2.1, 1], gap="large")
    with left_column:
        st.markdown("### Faça uma pergunta")
        with st.form("consulta_form", clear_on_submit=True):
            question = st.text_area(
                "Pergunta",
                placeholder="Faça uma pergunta sobre os TCCs...",
                height=120,
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "Enviar pergunta",
                type="primary",
                use_container_width=True,
                disabled=not api_available or not documents,
            )

        if submitted and question.strip():
            _submit_question(client, question.strip(), left_column)

        for message in st.session_state.chat_messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(message["content"])
                    if message.get("sources"):
                        render_sources(message.get("sources", []))
                    _render_times(message)

    with right_column:
        st.markdown(
            """
            <div class="hero-card">
                <div class="section-kicker">Fonte principal</div>
                <h3>Contexto recuperado para a resposta</h3>
                <p>O painel à direita destaca a fonte principal utilizada pela resposta do chatbot.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.selected_source:
            _render_selected_source(st.session_state.selected_source)
        else:
            st.info("Aguarde uma resposta para visualizar a fonte principal associada ao trecho recuperado.")


def _submit_question(client: APIClient, question: str, container: Any) -> None:
    top_k = 5
    st.session_state.chat_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o acervo e montando a resposta..."):
            try:
                payload = client.chat(question, top_k=top_k)
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

        if sources:
            st.session_state.selected_source = sources[0]
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


def _render_selected_source(source: dict[str, Any]) -> None:
    title = source.get("title") or "Título não identificado"
    author = source.get("author") or "Autor não identificado"
    year = source.get("year") or "Ano não informado"
    excerpt = source.get("excerpt") or "Trecho recuperado indisponível no momento."
    page = source.get("page_start")
    chapter = source.get("section") or "Seção não informada"

    st.markdown(
        f"""
        <div class="source-card">
            <div class="section-kicker">Fonte destacada</div>
            <h3>{title}</h3>
            <p><strong>Autor:</strong> {author}</p>
            <p><strong>Ano:</strong> {year}</p>
            <p><strong>Trecho recuperado:</strong> {excerpt}</p>
            <p><strong>Página:</strong> {page if page is not None else 'Não informada'}</p>
            <p><strong>Capítulo:</strong> {chapter}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Abrir PDF", use_container_width=True, disabled=True)
