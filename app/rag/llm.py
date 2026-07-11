"""Abstração e implementação HTTP para modelos de linguagem."""

from abc import ABC, abstractmethod

import httpx

from app.rag.exceptions import LLMProviderError, LLMTimeoutError


class LanguageModelProvider(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> str:
        """Gera uma resposta textual a partir de dois prompts."""


class OpenAICompatibleProvider(LanguageModelProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
    ) -> None:
        if not base_url.strip() or not model.strip():
            raise ValueError("LLM_BASE_URL e LLM_MODEL são obrigatórios")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Tempo limite excedido no provedor de LLM") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("Resposta inválida ou falha no provedor de LLM") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("O provedor de LLM retornou resposta vazia")
        return content.strip()


class UnavailableLLMProvider(LanguageModelProvider):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> str:
        del system_prompt, user_prompt, timeout_seconds
        raise LLMProviderError("Nenhum provedor de LLM foi configurado")
