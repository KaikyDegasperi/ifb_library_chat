import httpx
import pytest

from app.config import Settings
from app.rag.exceptions import LLMTimeoutError
from app.rag.factory import create_llm_provider
from app.rag.llm import OllamaChatProvider, OpenAICompatibleProvider


def test_create_llm_provider_supports_ollama_alias() -> None:
    settings = Settings(
        llm_provider="ollama",
        llm_base_url="http://localhost:11434",
        llm_model="qwen2.5:3b",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, OllamaChatProvider)


def test_ollama_provider_uses_chat_endpoint_and_preserves_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"message": {"content": "Resposta local"}}

    def fake_post(url: str, headers: dict[str, str] | None = None, json: dict[str, object] | None = None, timeout: float | None = None) -> DummyResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("app.rag.llm.httpx.post", fake_post)

    provider = OllamaChatProvider(
        base_url="http://localhost:11434",
        model="qwen2.5:3b",
    )
    response = provider.generate(
        system_prompt="sys",
        user_prompt="usr",
        timeout_seconds=4.5,
        max_tokens=128,
        temperature=0.1,
        top_p=0.9,
        context_window=2048,
    )

    assert response == "Resposta local"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["json"]["model"] == "qwen2.5:3b"
    assert captured["json"]["stream"] is False
    assert captured["json"]["options"]["temperature"] == 0.1
    assert captured["json"]["options"]["top_p"] == 0.9


@pytest.mark.parametrize(
    "provider",
    [
        OpenAICompatibleProvider("https://llm.example/v1", "model"),
        OllamaChatProvider("http://127.0.0.1:11434", "model"),
    ],
)
def test_llm_providers_apply_timeout_and_return_safe_error(
    monkeypatch,
    provider,
) -> None:
    secret = "provider-secret-that-must-not-leak"

    def timeout(*args, **kwargs):
        request = httpx.Request("POST", "https://llm.example")
        raise httpx.ReadTimeout(secret, request=request)

    monkeypatch.setattr("app.rag.llm.httpx.post", timeout)

    with pytest.raises(LLMTimeoutError, match="Tempo limite excedido") as error:
        provider.generate("system", "user", timeout_seconds=0.25)

    assert secret not in str(error.value)
