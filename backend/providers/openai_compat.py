"""
G-Mini Agent — Provider compatible con API OpenAI.
Un solo adaptador para: OpenAI, xAI (Grok), DeepSeek, Ollama, LM Studio.
Todos usan el mismo protocolo de API.
"""

from __future__ import annotations

from typing import AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from backend.providers.base import LLMProvider, LLMMessage, LLMResponse
from backend.config import config


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider unificado para todos los servicios con API compatible OpenAI.
    Cubre 5 de 7 proveedores con un solo adaptador.
    """

    def __init__(self, provider_name: str):
        self.name = provider_name
        self._client: AsyncOpenAI | None = None
        self._base_url: str = ""
        self._configure()

    def _configure(self) -> None:
        """Lee la configuración del provider desde config.yaml."""
        pconf = config.get("providers", self.name, default={})
        self._base_url = pconf.get("base_url", "")

        # Obtener API key del keyring (solo para providers cloud)
        api_key = "not-needed"  # Para locales (Ollama/LM Studio)
        vault = pconf.get("api_key_vault", "")
        if vault:
            stored_key = config.get_api_key(vault)
            if stored_key:
                api_key = stored_key

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=60.0,
        )

    def _build_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convierte LLMMessage a formato OpenAI API."""
        result = []
        for msg in messages:
            if msg.images:
                # Multimodal: content es una lista de partes
                content = [{"type": "text", "text": msg.content}]
                for img_b64 in msg.images:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    })
                result.append({"role": msg.role, "content": content})
            else:
                result.append({"role": msg.role, "content": msg.content})
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
        """Streaming generation."""
        if not self._client:
            self._configure()

        api_messages = self._build_messages(messages)

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"[{self.name}] Error en streaming: {e}")
            yield f"\n\n[Error del provider {self.name}: {str(e)}]"

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
            response = await self._client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **kwargs,
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                text=choice.message.content or "",
                model=model,
                provider=self.name,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                finish_reason=choice.finish_reason or "",
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error en generate_complete: {e}")
            return LLMResponse(
                text=f"Error: {str(e)}",
                model=model,
                provider=self.name,
            )

    async def list_models(self) -> list[str]:
        """Lista los modelos del provider."""
        # Para cloud: usar los de la config
        configured = config.get("providers", self.name, "models", default=[])
        if configured:
            return configured

        # Para locales: intentar descubrir via API
        if self.name in ("ollama", "lmstudio"):
            try:
                if not self._client:
                    self._configure()
                models = await self._client.models.list()
                return [m.id for m in models.data]
            except Exception as e:
                logger.debug(f"[{self.name}] No se pudieron listar modelos: {e}")
                return []

        return configured

    async def health_check(self) -> bool:
        """Verifica si el provider está disponible."""
        try:
            if not self._client:
                self._configure()
            models = await self._client.models.list()
            return True
        except Exception:
            return False
