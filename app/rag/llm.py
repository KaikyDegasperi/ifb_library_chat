"""Abstração e implementação HTTP para modelos de linguagem."""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.rag.exceptions import LLMProviderError, LLMTimeoutError


class LanguageModelProvider(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
        **generation_kwargs: Any,
    ) -> str:
        """Gera uma resposta textual a partir de dois prompts."""


class OpenAICompatibleProvider(LanguageModelProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        default_temperature: float = 0.1,
        default_top_p: float = 0.9,
        default_max_tokens: int | None = None,
    ) -> None:
        if not base_url.strip() or not model.strip():
            raise ValueError("LLM_BASE_URL e LLM_MODEL são obrigatórios")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens

    def _uses_openai_reasoning_parameters(self) -> bool:
        """Detecta modelos de raciocínio servidos pela API oficial da OpenAI."""
        model = self.model.strip().lower()
        return "api.openai.com" in self.base_url.lower() and model.startswith(
            ("gpt-5", "o1", "o3", "o4")
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
        **generation_kwargs: Any,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        uses_reasoning_parameters = self._uses_openai_reasoning_parameters()
        if uses_reasoning_parameters:
            payload["reasoning_effort"] = generation_kwargs.get(
                "reasoning_effort", "low"
            )
        else:
            payload["temperature"] = generation_kwargs.get(
                "temperature", self.default_temperature
            )
            payload["top_p"] = generation_kwargs.get("top_p", self.default_top_p)
        max_tokens = generation_kwargs.get("max_tokens", self.default_max_tokens)
        if max_tokens is not None:
            token_parameter = (
                "max_completion_tokens" if uses_reasoning_parameters else "max_tokens"
            )
            payload[token_parameter] = max_tokens
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
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


class OllamaChatProvider(LanguageModelProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        default_temperature: float = 0.1,
        default_top_p: float = 0.9,
        default_max_tokens: int | None = None,
        default_context_window: int | None = None,
        keep_alive: str | None = None,
    ) -> None:
        if not base_url.strip() or not model.strip():
            raise ValueError("LLM_BASE_URL e LLM_MODEL são obrigatórios")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        self.default_context_window = default_context_window
        self.keep_alive = keep_alive

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
        **generation_kwargs: Any,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        temperature = generation_kwargs.get("temperature", self.default_temperature)
        top_p = generation_kwargs.get("top_p", self.default_top_p)
        max_tokens = generation_kwargs.get("max_tokens", self.default_max_tokens)
        context_window = generation_kwargs.get(
            "context_window", self.default_context_window
        )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }
        if context_window is not None:
            payload["options"]["num_ctx"] = context_window
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
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
        **generation_kwargs: Any,
    ) -> str:
        del system_prompt, user_prompt, timeout_seconds, generation_kwargs
        raise LLMProviderError("Nenhum provedor de LLM foi configurado")
