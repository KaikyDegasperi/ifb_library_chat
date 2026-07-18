from streamlit.testing.v1 import AppTest


def test_multiple_sources_render_without_duplicate_widget_ids() -> None:
    app = AppTest.from_string(
        """
from frontend.components.sources import render_sources

render_sources([
    {
        "title": "Proposta de simulado de matemática unificado",
        "file_name": "simulado.pdf",
        "page_start": 11,
        "page_end": 12,
        "section": "Resultados",
        "score": 0.499,
    },
    {
        "title": "Proposta de simulado de matemática unificado",
        "file_name": "simulado.pdf",
        "page_start": 19,
        "page_end": 19,
        "section": "Considerações finais",
        "score": 0.452,
    },
])
"""
    ).run(timeout=10)

    assert not app.exception
