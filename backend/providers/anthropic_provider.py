"""
G-Mini Agent — Provider para Anthropic (Claude).
Usa el SDK nativo de Anthropic con streaming.
"""

from __future__ import annotations

from typing import AsyncGenerator

from loguru import logger
from anthropic import AsyncAnthropic

from backend.providers.base import LLMProvider, LLMMessage, LLMResponse
from backend.config import config


class AnthropicProvider(LLMProvider):
    """Provider para modelos Claude de Anthropic."""

    name = "anthropic"

    def __init__(self):
        self._client: AsyncAnthropic | None = None
        self._configure()

    def _configure(self) -> None:
        vault = config.get("providers", "anthropic", "api_key_vault", default="anthropic_api")
        api_key = config.get_api_key(vault) or ""

        self._client = AsyncAnthropic(
            api_key=api_key,
            timeout=60.0,
        )

    def _build_messages(self, messages: list[LLMMessage]) -> tuple[str, list[dict]]:
        """
        Convierte LLMMessage al formato Anthropic.
        Separa el system prompt de los mensajes.
        Retorna (system_prompt, messages).
        """
        system_prompt = ""
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
                continue

            if msg.images:
                content = [{"type": "text", "text": msg.content}]
                for img_b64 in msg.images:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_b64,
                        },
                    })
                api_messages.append({"role": msg.role, "content": content})
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        return system_prompt.strip(), api_messages

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation con Anthropic."""
        if not self._client:
            self._configure()

        system_prompt, api_messages = self._build_messages(messages)

        try:
            async with self._client.messages.stream(
                model=model,
                messages=api_messages,
                system=system_prompt if system_prompt else "You are a helpful assistant.",
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream_response:
                async for text in stream_response.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"[anthropic] Error en streaming: {e}")
            yield f"\n\n[Error del provider Anthropic: {str(e)}]"

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

        system_prompt, api_messages = self._build_messages(messages)

        try:
            response = await self._client.messages.create(
                model=model,
                messages=api_messages,
                system=system_prompt if system_prompt else "You are a helpful assistant.",
                temperature=temperature,
                max_tokens=max_tokens,
            )

            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            return LLMResponse(
                text=text,
                model=model,
                provider="anthropic",
                input_tokens=response.usage.input_tokens if response.usage else 0,
                output_tokens=response.usage.output_tokens if response.usage else 0,
                finish_reason=response.stop_reason or "",
            )

        except Exception as e:
            logger.error(f"[anthropic] Error en generate_complete: {e}")
            return LLMResponse(text=f"Error: {str(e)}", model=model, provider="anthropic")

    async def list_models(self) -> list[str]:
        return config.get("providers", "anthropic", "models", default=[])

    async def health_check(self) -> bool:
        try:
            if not self._client:
                self._configure()
            # Un message mínimo para verificar conectividad
            response = await self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False
