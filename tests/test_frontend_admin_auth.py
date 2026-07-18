from streamlit.testing.v1 import AppTest


def test_admin_token_is_kept_in_session_and_hidden_after_submission() -> None:
    token = "session-token-that-must-not-be-rendered"
    app = AppTest.from_string(
        """
from frontend.pages.documents import render_documents_page

class FakeClient:
    pass

render_documents_page(FakeClient(), [], True)
"""
    ).run(timeout=10)

    assert not app.exception
    assert [item.label for item in app.text_input] == ["Token administrativo"]

    app.text_input[0].input(token)
    app.button[0].click().run(timeout=10)

    assert not app.exception
    assert app.session_state["admin_api_token"] == token
    assert not app.text_input
    assert token not in " ".join(item.value for item in app.markdown)
    assert token not in " ".join(item.value for item in app.success)
