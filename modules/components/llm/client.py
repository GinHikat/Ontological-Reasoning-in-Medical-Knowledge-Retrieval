from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from modules.components.llm.schemas import DEFAULT_MODEL


LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class LocalLLMClientError(RuntimeError):
    """Raised for local LLM connectivity or protocol failures."""


@dataclass
class LocalChatLLMClient:
    """OpenAI-compatible chat client restricted to local endpoints."""

    base_url: str = "http://127.0.0.1:8000/v1"
    model: str = DEFAULT_MODEL
    timeout: float = 300.0
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    enable_thinking: bool = False
    allow_non_local: bool = False
    extra_body: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._validate_local_host()

    def _validate_local_host(self) -> None:
        parsed = urlparse(self.base_url)
        host = (parsed.hostname or "").lower()
        if not host:
            raise LocalLLMClientError(f"Invalid base_url (missing host): {self.base_url}")
        if host in LOCAL_HOSTS:
            return
        if self.allow_non_local:
            return
        raise LocalLLMClientError(
            f"Refusing non-local LLM host '{host}'. "
            "Only 127.0.0.1 / localhost / ::1 are allowed by default. "
            "Set allow_non_local=True only for explicit development overrides "
            "(never for competition inference)."
        )

    @property
    def generation_settings(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "enable_thinking": self.enable_thinking,
            "base_url": self.base_url,
        }

    def _chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _health_url(self) -> str:
        # OpenAI-compatible servers usually expose /models under the same /v1 prefix.
        return f"{self.base_url}/models"

    def _request_json(
        self, url: str, payload: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        data = None
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer EMPTY",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LocalLLMClientError(
                f"HTTP {exc.code} from local LLM at {url}: {detail}"
            ) from exc
        except URLError as exc:
            raise LocalLLMClientError(
                f"Cannot connect to local LLM at {url}: {exc.reason}. "
                "Is vLLM serving on the configured host/port?"
            ) from exc
        except TimeoutError as exc:
            raise LocalLLMClientError(
                f"Timed out after {self.timeout}s waiting for local LLM at {url}"
            ) from exc
        except socket.timeout as exc:
            raise LocalLLMClientError(
                f"Socket timeout after {self.timeout}s waiting for local LLM at {url}"
            ) from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LocalLLMClientError(
                f"Local LLM returned non-JSON body from {url}: {body[:500]}"
            ) from exc
        if not isinstance(parsed, dict):
            raise LocalLLMClientError(f"Expected JSON object from {url}, got {type(parsed)}")
        return parsed

    def health_check(self) -> dict[str, Any]:
        """Return /models payload if the local server is reachable."""
        return self._request_json(self._health_url())

    def is_healthy(self) -> bool:
        try:
            self.health_check()
            return True
        except LocalLLMClientError:
            return False

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[dict[str, Any]] = None,
    ) -> str:
        """Call local /chat/completions and return the assistant message content."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "top_p": self.top_p if top_p is None else top_p,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        # Qwen3.5 / vLLM thinking control (OpenAI-compatible extra fields).
        chat_template_kwargs = {"enable_thinking": self.enable_thinking}
        payload["chat_template_kwargs"] = chat_template_kwargs
        merged_extra = dict(self.extra_body)
        if extra_body:
            merged_extra.update(extra_body)
        if merged_extra:
            payload.update(merged_extra)

        response = self._request_json(self._chat_url(), payload)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LocalLLMClientError(
                f"Unexpected chat.completions shape: {json.dumps(response)[:800]}"
            ) from exc
        if content is None:
            # Some reasoning models put text in reasoning_content when thinking is on.
            message = response["choices"][0]["message"]
            content = message.get("reasoning_content") or ""
        return str(content)
