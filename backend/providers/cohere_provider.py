"""
G-Mini Agent — Provider para Cohere (Command R).
Usa el SDK oficial de Cohere con streaming.
"""

from __future__ import annotations

from typing import AsyncGenerator

from loguru import logger

from backend.providers.base import LLMProvider, LLMMessage, LLMResponse
from backend.config import config

try:
    import cohere

    HAS_COHERE = True
except ImportError:
    HAS_COHERE = False
    cohere = None  # type: ignore[assignment]


class CohereProvider(LLMProvider):
    """Provider para modelos Command de Cohere."""

    name = "cohere"

    def __init__(self):
        if not HAS_COHERE:
            raise ImportError(
                "El SDK de Cohere no está instalado. Ejecuta: pip install cohere"
            )
        self._client: cohere.AsyncClientV2 | None = None
        self._configure()

    def _configure(self) -> None:
        vault = config.get(
            "providers", "cohere", "api_key_vault", default="cohere_api"
        )
        api_key = config.get_api_key(vault) or ""
        self._client = cohere.AsyncClientV2(api_key=api_key, timeout=60)

    def _build_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convierte LLMMessage al formato Cohere Chat v2."""
        result: list[dict] = []
        for msg in messages:
            role = msg.role
            if role == "system":
                role = "system"
            elif role == "assistant":
                role = "assistant"
            else:
                role = "user"
            result.append({"role": role, "content": msg.content})
        return result

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation con Cohere."""
        if not self._client:
            self._configure()

        api_messages = self._build_messages(messages)

        try:
            response = self._client.chat_stream(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            async for event in response:
                if event.type == "content-delta" and hasattr(event, "delta"):
                    text = getattr(event.delta, "message", None)
                    if text and hasattr(text, "content") and text.content:
                        content = text.content
                        if isinstance(content, list):
                            for part in content:
                                if hasattr(part, "text"):
                                    yield part.text
                        elif isinstance(content, str):
                            yield content

        except Exception as e:
            logger.error(f"[cohere] Error en streaming: {e}")
            yield f"\n\n[Error del provider Cohere: {str(e)}]"

    async def generate_complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Non-streaming generation."""
        if not self._client:
            self._configure()

        api_messages = self._build_messages(messages)

        try:
            response = await self._client.chat(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            text = ""
            if response.message and response.message.content:
                for part in response.message.content:
                    if hasattr(part, "text"):
                        text += part.text

            usage = response.usage if hasattr(response, "usage") else None
            return LLMResponse(
                text=text,
                model=model,
                provider="cohere",
                input_tokens=getattr(usage, "tokens", {}).get("input_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "tokens", {}).get("output_tokens", 0) if usage else 0,
                finish_reason=getattr(response, "finish_reason", "") or "",
            )

        except Exception as e:
            logger.error(f"[cohere] Error en generate_complete: {e}")
            return LLMResponse(
                text=f"Error: {str(e)}", model=model, provider="cohere"
            )

    async def list_models(self) -> list[str]:
        return config.get("providers", "cohere", "models", default=[])

    async def health_check(self) -> bool:
        try:
            if not self._client:
                self._configure()
            response = await self._client.chat(
                model="command-light",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False
