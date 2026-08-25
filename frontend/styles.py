"""Sistema visual institucional da interface Streamlit."""

import streamlit as st


APP_CSS = r"""
<style>
:root {
    --ifb-green: #0b6b45;
    --ifb-green-dark: #075237;
    --ifb-lime: #d9ef42;
    --ifb-ink: #17201c;
    --ifb-muted: #6b746f;
    --ifb-line: #e1e6e3;
    --ifb-paper: #fbfcfa;
    --ifb-sidebar: #f1f4f1;
    --ifb-surface: #ffffff;
    --ifb-surface-subtle: #f8faf8;
    --ifb-surface-hover: #f5f8f6;
    --ifb-surface-raised: #f3f7f4;
    --ifb-profile-bg: #e6ebe7;
    --ifb-user-message: #edf1ee;
    --ifb-body-text: #26332d;
    --ifb-border-strong: #d8e0db;
    --ifb-input-border: #cfd8d2;
    --ifb-success: #36a76f;
    --ifb-success-ring: #dff2e8;
    --ifb-danger: #c85d54;
    --ifb-danger-ring: #f4dedb;
    --ifb-shadow: rgba(24, 55, 39, 0.12);
    --ifb-shadow-soft: rgba(24, 55, 39, 0.08);
}

.stApp {
    background: var(--ifb-paper);
    color: var(--ifb-ink);
}

header[data-testid="stHeader"] {
    height: 0;
    min-height: 0;
    overflow: visible;
    background: transparent;
    border-bottom: 0;
}

/* Reserva o cabeçalho somente quando o menu lateral estiver fechado. */
header[data-testid="stHeader"]:has([data-testid="stExpandSidebarButton"]) {
    height: 3.75rem;
    min-height: 3.75rem;
    overflow: visible;
    pointer-events: none;
}

[data-testid="stDecoration"] {
    display: none !important;
}

/* Mantém o menu nativo acessível para a troca entre os temas claro e escuro. */
[data-testid="stHeaderActionElements"] {
    position: fixed !important;
    top: 0.75rem;
    right: 0.75rem;
    z-index: 1000000;
    display: flex !important;
    pointer-events: auto;
}

/* O botão de reabrir a lateral vive dentro da toolbar do Streamlit. */
[data-testid="stToolbar"] {
    display: flex !important;
    height: 0;
    min-height: 0;
    overflow: visible;
    pointer-events: none;
}

[data-testid="stToolbar"]:has([data-testid="stExpandSidebarButton"]) {
    height: 3.75rem;
    min-height: 3.75rem;
    overflow: visible;
}

[data-testid="stExpandSidebarButton"] {
    position: fixed !important;
    top: 0.75rem;
    left: 0.75rem;
    z-index: 1000000;
    width: 2.5rem;
    height: 2.5rem;
    display: grid !important;
    place-items: center;
    pointer-events: auto;
    border: 1px solid var(--ifb-line);
    border-radius: 10px;
    background: var(--ifb-surface);
    box-shadow: 0 6px 18px var(--ifb-shadow);
}

[data-testid="stExpandSidebarButton"]:hover {
    color: var(--ifb-green-dark);
    border-color: var(--ifb-border-strong);
    background: var(--ifb-surface-hover);
}

[data-testid="stSidebar"] {
    background: var(--ifb-sidebar);
    border-right: 1px solid var(--ifb-line);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1rem;
}

.block-container {
    max-width: 1120px;
    padding-top: 1.8rem;
    padding-bottom: 7rem;
}

h1, h2, h3 {
    color: var(--ifb-ink);
    letter-spacing: -0.025em;
}

p, label, [data-testid="stCaptionContainer"] {
    color: var(--ifb-muted);
}

.ifb-brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.2rem 0 1.1rem;
}

.ifb-brand-mark {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    border: 2px solid var(--ifb-green);
    border-radius: 10px 10px 10px 3px;
    color: var(--ifb-green);
    font-weight: 850;
    font-size: 0.8rem;
    position: relative;
}

.ifb-brand-mark::after {
    content: "";
    position: absolute;
    width: 7px;
    height: 7px;
    right: 3px;
    top: 3px;
    border-radius: 50%;
    background: var(--ifb-lime);
}

.ifb-brand-copy strong,
.ifb-brand-copy small {
    display: block;
}

.ifb-brand-copy strong {
    color: var(--ifb-ink);
    font-size: 0.9rem;
}

.ifb-brand-copy small {
    color: var(--ifb-muted);
    font-size: 0.7rem;
    margin-top: 0.1rem;
}

.sidebar-label {
    color: var(--ifb-muted);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 750;
    margin: 1rem 0 0.35rem;
}

.history-item {
    color: var(--ifb-muted);
    font-size: 0.76rem;
    line-height: 1.35;
    padding: 0.42rem 0.3rem;
    border-bottom: 1px solid var(--ifb-line);
}

.ifb-profile {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-top: 0.9rem;
    padding: 0.65rem;
    border-radius: 10px;
    background: var(--ifb-profile-bg);
}

.ifb-profile > span {
    width: 31px;
    height: 31px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    background: var(--ifb-green);
    color: white;
    font-size: 0.65rem;
    font-weight: 750;
}

.ifb-profile strong,
.ifb-profile small {
    display: block;
}

.ifb-profile strong {
    color: var(--ifb-ink);
    font-size: 0.72rem;
}

.ifb-profile small {
    color: var(--ifb-muted);
    font-size: 0.62rem;
    margin-top: 0.1rem;
}

.status-bar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.45rem;
    min-height: 24px;
    color: var(--ifb-muted);
    font-size: 0.72rem;
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--ifb-success);
    box-shadow: 0 0 0 3px var(--ifb-success-ring);
}

.status-dot.offline {
    background: var(--ifb-danger);
    box-shadow: 0 0 0 3px var(--ifb-danger-ring);
}

.welcome-shell {
    max-width: 780px;
    margin: 4.5rem auto 1.75rem;
    text-align: center;
}

.st-key-chat_window {
    max-width: 920px;
    margin: 1rem auto 0;
    padding: 0 !important;
    overflow: hidden;
    border: 1px solid var(--ifb-border-strong) !important;
    border-radius: 18px !important;
    background: var(--ifb-surface);
    box-shadow: 0 18px 50px var(--ifb-shadow-soft);
}

.chat-window-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.15rem;
    border-bottom: 1px solid var(--ifb-line);
    background: var(--ifb-surface-subtle);
}

.chat-window-identity {
    display: flex;
    align-items: center;
    gap: 0.7rem;
}

.chat-window-mark {
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    flex: none;
    border-radius: 11px 11px 11px 4px;
    background: var(--ifb-green);
    color: var(--ifb-lime);
    font-size: 1.1rem;
}

.chat-window-identity strong,
.chat-window-identity small {
    display: block;
}

.chat-window-identity strong {
    color: var(--ifb-ink);
    font-size: 0.88rem;
}

.chat-window-identity small {
    margin-top: 0.1rem;
    color: var(--ifb-muted);
    font-size: 0.68rem;
}

.chat-window-status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--ifb-muted);
    font-size: 0.68rem;
}

.chat-status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--ifb-success);
    box-shadow: 0 0 0 3px var(--ifb-success-ring);
}

.chat-status-dot.offline {
    background: var(--ifb-danger);
    box-shadow: 0 0 0 3px var(--ifb-danger-ring);
}

.st-key-chat_history {
    padding: 0.35rem 1rem 0.75rem;
    background: var(--ifb-surface);
}

.st-key-chat_window [data-testid="stChatInput"] {
    margin: 0 1rem;
}

.st-key-chat_window > div:last-child [data-testid="stCaptionContainer"] {
    padding: 0 1rem 0.7rem;
    text-align: center;
}

.welcome-shell.isolated {
    margin: 2.4rem auto 1.4rem;
}

.welcome-shell.isolated h1 {
    font-size: clamp(2rem, 4vw, 2.8rem);
}

.ai-mark {
    width: 56px;
    height: 56px;
    display: grid;
    place-items: center;
    margin: 0 auto 1.1rem;
    border-radius: 17px 17px 17px 6px;
    background: var(--ifb-green);
    color: var(--ifb-lime);
    box-shadow: 0 9px 25px rgba(11, 107, 69, 0.16);
    font-size: 1.65rem;
}

.eyebrow,
.answer-label,
.section-kicker {
    color: var(--ifb-green);
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.welcome-shell h1 {
    max-width: 720px;
    margin: 0.65rem auto 0.8rem;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2.25rem, 5vw, 3.35rem);
    line-height: 1.08;
    font-weight: 500;
}

.welcome-shell .intro {
    max-width: 630px;
    margin: 0 auto;
    color: var(--ifb-muted);
    font-size: 0.92rem;
    line-height: 1.75;
}

.collection-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 1rem;
    padding: 0.35rem 0.65rem;
    border: 1px solid var(--ifb-border-strong);
    border-radius: 999px;
    background: var(--ifb-surface-raised);
    color: var(--ifb-green-dark);
    font-size: 0.7rem;
    font-weight: 650;
}

.hero-card,
.metric-card,
.source-card {
    background: var(--ifb-surface);
    border: 1px solid var(--ifb-line);
    border-radius: 14px;
    padding: 1.25rem 1.35rem;
    box-shadow: 0 8px 24px var(--ifb-shadow-soft);
}

.hero-card {
    margin: 1.25rem 0 1.5rem;
    background: linear-gradient(135deg, var(--ifb-surface) 0%, var(--ifb-surface-raised) 100%);
}

.hero-card h1 {
    margin: 0.55rem 0 0.45rem;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2rem, 4vw, 3rem);
    font-weight: 500;
}

.hero-card p,
.source-card p {
    margin-bottom: 0;
}

.hero-card.compact {
    margin-bottom: 1rem;
    padding: 1rem 1.2rem;
}

.hero-card.compact h1 {
    margin-top: 0.35rem;
    font-size: clamp(1.75rem, 3vw, 2.35rem);
}

.hero-card.compact p {
    margin-top: 0.3rem;
}

.metric-card {
    min-height: 112px;
}

.metric-card h2 {
    margin: 0.45rem 0 0;
    color: var(--ifb-green-dark);
}

.source-card {
    margin: 0.7rem 0;
    padding: 0.9rem 1rem;
}

.source-card h4 {
    margin: 0 0 0.35rem;
    color: var(--ifb-ink);
}

.source-card p {
    font-size: 0.78rem;
    line-height: 1.45;
}

[data-testid="stChatMessage"] {
    max-width: 820px;
    margin-left: auto;
    margin-right: auto;
    padding: 1rem 0.75rem;
    border-radius: 12px;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--ifb-user-message);
}

[data-testid="stChatMessage"] p {
    color: var(--ifb-body-text);
    line-height: 1.7;
}

[data-testid="stChatInput"] {
    border-color: var(--ifb-input-border);
    border-radius: 15px;
    background: var(--ifb-surface);
    box-shadow: 0 10px 32px var(--ifb-shadow-soft);
}

[data-testid="stChatInput"] textarea {
    color: var(--ifb-ink);
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    min-height: 2.55rem;
    border-radius: 10px;
    font-weight: 650;
    transition: transform 0.16s ease, box-shadow 0.16s ease;
}

/* Mantém texto e ícones legíveis nos botões verdes, inclusive desabilitados. */
button[data-testid="stBaseButton-primary"],
button[kind="primary"],
button[data-testid="stBaseButton-primary"]:disabled,
button[kind="primary"]:disabled {
    color: #ffffff !important;
}

button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] span,
button[kind="primary"] p,
button[kind="primary"] span {
    color: #ffffff !important;
}

button[data-testid="stBaseButton-primary"] svg,
button[kind="primary"] svg {
    color: #ffffff !important;
    fill: currentColor;
}

button[data-testid="stBaseButton-primary"]:disabled,
button[kind="primary"]:disabled {
    border-color: var(--ifb-green) !important;
    background: var(--ifb-green) !important;
    opacity: 1;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 7px 18px rgba(11, 107, 69, 0.12);
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stFileUploaderDropzone"] {
    border-color: var(--ifb-input-border);
    border-radius: 10px;
    background: var(--ifb-surface);
}

[data-testid="stAlert"] {
    border-radius: 12px;
}

@media (max-width: 800px) {
    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .welcome-shell {
        margin-top: 2rem;
    }

    .st-key-chat_window {
        margin-top: 0.25rem;
        border-radius: 14px !important;
    }

    .chat-window-status {
        display: none;
    }

    /* Evita que a sidebar aberta espreme o conteúdo em telas estreitas
       (celular e tablet retrato): ela passa a flutuar sobre a página
       em vez de dividir a largura com o conteúdo principal. */
    [data-testid="stSidebar"] {
        position: fixed !important;
        top: 0;
        height: 100dvh !important;
        z-index: 999997;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.28);
    }

    /* Altura do histórico de conversa acompanha telas curtas (ex.: celular
       na horizontal), para o campo de pergunta não ficar fora da tela. */
    .st-key-chat_history {
        height: min(520px, 60dvh) !important;
    }
}
</style>
"""

DARK_MODE_CSS = r"""
<style>
:root {
    --ifb-green: #2aa876;
    --ifb-green-dark: #63d4a4;
    --ifb-lime: #d9ef42;
    --ifb-ink: #e7efea;
    --ifb-muted: #a8b8af;
    --ifb-line: #33443a;
    --ifb-paper: #101713;
    --ifb-sidebar: #131d18;
    --ifb-surface: #18221d;
    --ifb-surface-subtle: #1c2922;
    --ifb-surface-hover: #24342b;
    --ifb-surface-raised: #202e27;
    --ifb-profile-bg: #1c2922;
    --ifb-user-message: #223229;
    --ifb-body-text: #dce7e0;
    --ifb-border-strong: #405449;
    --ifb-input-border: #405449;
    --ifb-success: #47c792;
    --ifb-success-ring: #173d2e;
    --ifb-danger: #f08078;
    --ifb-danger-ring: #492624;
    --ifb-shadow: rgba(0, 0, 0, 0.32);
    --ifb-shadow-soft: rgba(0, 0, 0, 0.24);
}
</style>
"""


def apply_styles() -> None:
    """Aplica os detalhes visuais que complementam o tema nativo."""
    mode_css = DARK_MODE_CSS if st.context.theme.type == "dark" else ""
    st.markdown(APP_CSS + mode_css, unsafe_allow_html=True)
