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

[data-testid="stHeaderActionElements"],
[data-testid="stDecoration"] {
    display: none !important;
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
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(24, 55, 39, 0.12);
}

[data-testid="stExpandSidebarButton"]:hover {
    color: var(--ifb-green-dark);
    border-color: #b8c9bf;
    background: #f5f8f6;
}

[data-testid="stSidebar"] {
    background: var(--ifb-sidebar);
    border-right: 1px solid #dce2de;
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
    color: #8a938e;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 750;
    margin: 1rem 0 0.35rem;
}

.history-item {
    color: #53605a;
    font-size: 0.76rem;
    line-height: 1.35;
    padding: 0.42rem 0.3rem;
    border-bottom: 1px solid rgba(220, 226, 222, 0.65);
}

.ifb-profile {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-top: 0.9rem;
    padding: 0.65rem;
    border-radius: 10px;
    background: #e6ebe7;
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
    color: #7a857f;
    font-size: 0.62rem;
    margin-top: 0.1rem;
}

.status-bar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.45rem;
    min-height: 24px;
    color: #7b857f;
    font-size: 0.72rem;
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #36a76f;
    box-shadow: 0 0 0 3px #dff2e8;
}

.status-dot.offline {
    background: #c85d54;
    box-shadow: 0 0 0 3px #f4dedb;
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
    border: 1px solid #d8e0db !important;
    border-radius: 18px !important;
    background: #ffffff;
    box-shadow: 0 18px 50px rgba(24, 55, 39, 0.08);
}

.chat-window-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.15rem;
    border-bottom: 1px solid var(--ifb-line);
    background: #f8faf8;
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
    background: #36a76f;
    box-shadow: 0 0 0 3px #dff2e8;
}

.chat-status-dot.offline {
    background: #c85d54;
    box-shadow: 0 0 0 3px #f4dedb;
}

.st-key-chat_history {
    padding: 0.35rem 1rem 0.75rem;
    background: #ffffff;
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
    border: 1px solid #d5e2da;
    border-radius: 999px;
    background: #f3f7f4;
    color: var(--ifb-green-dark);
    font-size: 0.7rem;
    font-weight: 650;
}

.hero-card,
.metric-card,
.source-card {
    background: #ffffff;
    border: 1px solid var(--ifb-line);
    border-radius: 14px;
    padding: 1.25rem 1.35rem;
    box-shadow: 0 8px 24px rgba(28, 62, 43, 0.04);
}

.hero-card {
    margin: 1.25rem 0 1.5rem;
    background: linear-gradient(135deg, #ffffff 0%, #f4f8f5 100%);
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
    background: #edf1ee;
}

[data-testid="stChatMessage"] p {
    color: #26332d;
    line-height: 1.7;
}

[data-testid="stChatInput"] {
    border-color: #cfd8d2;
    border-radius: 15px;
    background: #ffffff;
    box-shadow: 0 10px 32px rgba(21, 52, 38, 0.08);
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
    border-color: #d9dfdb;
    border-radius: 10px;
    background: #ffffff;
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
}
</style>
"""


def apply_styles() -> None:
    """Aplica os detalhes visuais que complementam o tema nativo."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
