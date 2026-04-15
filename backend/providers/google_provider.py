"""
G-Mini Agent — Provider para Google (Gemini).
Usa el SDK google-genai con streaming.
"""

from __future__ import annotations

from typing import AsyncGenerator

from loguru import logger

from backend.providers.base import LLMProvider, LLMMessage, LLMResponse
from backend.config import config


class GoogleProvider(LLMProvider):
    """Provider para modelos Gemini de Google."""

    name = "google"

    def __init__(self):
        self._client = None
        self._configure()

    def _configure(self) -> None:
        try:
            from google import genai

            vault = config.get("providers", "google", "api_key_vault", default="google_api")
            api_key = config.get_api_key(vault) or ""

            if not api_key:
                raise ValueError("No API key was provided. Please pass a valid API key.")

            self._client = genai.Client(api_key=api_key)
        except Exception as e:
            self._client = None
            raise

    def _build_contents(self, messages: list[LLMMessage]) -> tuple[str | None, list]:
        """
        Convierte LLMMessage al formato Google genai.
        Retorna (system_instruction, contents).
        """
        from google.genai import types

        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
                continue

            role = "user" if msg.role == "user" else "model"

            if msg.images:
                import base64
                parts = [types.Part.from_text(text=msg.content)]
                for img_b64 in msg.images:
                    img_bytes = base64.b64decode(img_b64)
                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                contents.append(types.Content(role=role, parts=parts))
            else:
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.content)],
                ))

        return system_instruction, contents

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation con Gemini."""
        if not self._client:
            self._configure()

        from google.genai import types
        import asyncio

        system_instruction, contents = self._build_contents(messages)

        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        try:
            # generate_content_stream es síncrono — usar Queue como puente para streaming real
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[str | None] = asyncio.Queue()

            def _sync_stream():
                try:
                    response = self._client.models.generate_content_stream(
                        model=model,
                        contents=contents,
                        config=gen_config,
                    )
                    for chunk in response:
                        if chunk.text:
                            loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, exc)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

            loop.run_in_executor(None, _sync_stream)

            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item

        except Exception as e:
            logger.error(f"[google] Error en streaming: {e}")
            yield f"\n\n[Error del provider Google: {str(e)}]"

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

        from google.genai import types

        system_instruction, contents = self._build_contents(messages)

        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        try:
            import asyncio as _asyncio
            _loop = _asyncio.get_running_loop()

            def _sync_complete():
                return self._client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=gen_config,
                )

            response = await _loop.run_in_executor(None, _sync_complete)

            text = response.text or ""
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

            return LLMResponse(
                text=text,
                model=model,
                provider="google",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as e:
            logger.error(f"[google] Error en generate_complete: {e}")
            return LLMResponse(text=f"Error: {str(e)}", model=model, provider="google")

    async def list_models(self) -> list[str]:
        return config.get("providers", "google", "models", default=[])

    async def health_check(self) -> bool:
        try:
            if not self._client:
                self._configure()
            import asyncio as _asyncio
            _loop = _asyncio.get_running_loop()
            client = self._client

            def _sync_ping():
                client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents="ping",
                )

            await _loop.run_in_executor(None, _sync_ping)
            return True
        except Exception:
            return False
