"""
G-Mini Agent - Router de proveedores LLM.
Selecciona el provider correcto segun config, con fallback automatico.
Integra cost-aware routing via CostOptimizer (Fase 9.4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncGenerator

import yaml
from loguru import logger

from backend.config import config
from backend.providers.base import LLMProvider, LLMMessage, LLMResponse, LLMProviderUnavailableError
from backend.providers.openai_compat import OpenAICompatibleProvider
from backend.providers.anthropic_provider import AnthropicProvider
from backend.providers.google_provider import GoogleProvider
from backend.providers.cohere_provider import CohereProvider


# Providers que usan la API compatible OpenAI
OPENAI_COMPAT_PROVIDERS = {
    "openai", "xai", "deepseek", "ollama", "lmstudio",
    "groq", "mistral", "perplexity", "openrouter",
}


class ModelRouter:
    """
    Selector inteligente de proveedor LLM.
    - Instancia el provider correcto segun el modelo seleccionado.
    - Implementa fallback automatico si un provider falla.
    """

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._last_generation_meta: dict[str, str | bool] = {
            "provider": "",
            "model": "",
            "requested_provider": "",
            "requested_model": "",
            "fallback": False,
        }
        self._last_optimization: Any = None
        self._models_catalog: dict | None = None
        self._initialize_providers()

    # ── Catálogo models.yaml ──────────────────────────────────────
    def _get_models_catalog(self) -> dict:
        """Lee y cachea data/models.yaml."""
        if self._models_catalog is not None:
            return self._models_catalog
        try:
            yaml_path = Path(__file__).resolve().parent.parent.parent / "data" / "models.yaml"
            with open(yaml_path, "r", encoding="utf-8") as f:
                self._models_catalog = yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning(f"No se pudo leer models.yaml en router: {exc}")
            self._models_catalog = {}
        return self._models_catalog

    def _get_model_meta(self, provider_name: str, model: str) -> dict:
        """Devuelve metadatos de un modelo desde el catálogo. Dict vacío si no existe."""
        catalog = self._get_models_catalog()
        provider_models = catalog.get("llm", {}).get(provider_name, {})
        if isinstance(provider_models, dict):
            return provider_models.get(model, {}) if isinstance(provider_models.get(model), dict) else {}
        return {}

    def _validate_model_for_text_chat(self, provider_name: str, model: str) -> None:
        """
        Valida que el modelo sea compatible con generateContent (chat de texto).
        Lanza ValueError si el modelo es live-only (api_method: 'live').
        """
        meta = self._get_model_meta(provider_name, model)
        if not meta:
            return  # Modelo no está en catálogo con metadata → permitir (providers simples)
        api_method = meta.get("api_method", "")
        if api_method == "live":
            display = meta.get("display_name", model)
            raise ValueError(
                f"El modelo '{display}' solo funciona con la Live API (voz en tiempo real). "
                f"No soporta chat de texto (generateContent). "
                f"Cambia a otro modelo en Settings o usa el modo de voz."
            )

    def _initialize_providers(self) -> None:
        """Crea instancias de todos los providers configurados."""
        for name in OPENAI_COMPAT_PROVIDERS:
            try:
                self._providers[name] = OpenAICompatibleProvider(name)
                logger.debug(f"Provider inicializado: {name}")
            except Exception as exc:
                logger.warning(f"No se pudo inicializar provider {name}: {exc}")

        try:
            self._providers["anthropic"] = AnthropicProvider()
            logger.debug("Provider inicializado: anthropic")
        except Exception as exc:
            logger.warning(f"No se pudo inicializar provider anthropic: {exc}")

        try:
            self._providers["google"] = GoogleProvider()
            logger.debug("Provider inicializado: google")
        except Exception as exc:
            logger.warning(f"No se pudo inicializar provider google: {exc}")

        try:
            self._providers["cohere"] = CohereProvider()
            logger.debug("Provider inicializado: cohere")
        except Exception as exc:
            logger.warning(f"No se pudo inicializar provider cohere: {exc}")

    def get_provider(self, provider_name: str | None = None) -> LLMProvider | None:
        """Obtiene un provider por nombre. Si no se especifica, usa el default."""
        if provider_name is None:
            provider_name = config.get("model_router", "default_provider", default="openai")
        return self._providers.get(provider_name)

    def get_current_model(self) -> str:
        """Retorna el modelo activo actual."""
        return config.get("model_router", "default_model", default="gpt-5.4")

    def get_current_provider_name(self) -> str:
        """Retorna el nombre del provider activo."""
        return config.get("model_router", "default_provider", default="openai")

    def _set_last_generation_meta(
        self,
        *,
        provider: str,
        model: str,
        requested_provider: str,
        requested_model: str,
        fallback: bool,
    ) -> None:
        self._last_generation_meta = {
            "provider": provider,
            "model": model,
            "requested_provider": requested_provider,
            "requested_model": requested_model,
            "fallback": fallback,
        }

    def get_last_generation_meta(self) -> dict[str, str | bool]:
        return dict(self._last_generation_meta)

    async def _resolve_fallback_candidates(
        self,
        requested_provider: str,
        requested_model: str,
    ) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = {(requested_provider, requested_model)}
        fallback_order = config.get("model_router", "fallback_order", default=[])
        for fallback_entry in fallback_order:
            parts = str(fallback_entry or "").split(":", 1)
            if not parts or not parts[0]:
                continue
            if parts[0] == "local" and len(parts) > 1:
                fb_provider = parts[1]
                fb_model = await self._get_local_model(fb_provider)
                if not fb_model:
                    logger.debug(f"No hay modelos disponibles en {fb_provider}")
                    continue
            else:
                fb_provider = parts[0]
                fb_model = parts[1] if len(parts) > 1 else requested_model

            candidate = (fb_provider, fb_model)
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
        return candidates

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        provider_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta con fallback automatico.
        Si el provider principal falla, intenta con los del fallback_order.
        """
        if model is None:
            model = self.get_current_model()
        if provider_name is None:
            provider_name = self.get_current_provider_name()

        # Validar que el modelo soporte generateContent (no sea live-only)
        self._validate_model_for_text_chat(provider_name, model)

        provider = self.get_provider(provider_name)
        if provider:
            try:
                self._set_last_generation_meta(
                    provider=provider_name,
                    model=model,
                    requested_provider=provider_name,
                    requested_model=model,
                    fallback=False,
                )
                async for chunk in provider.generate(
                    messages, model, temperature, max_tokens, stream, **kwargs
                ):
                    yield chunk
                return
            except Exception as exc:
                logger.warning(f"Provider {provider_name} fallo: {exc}")

        for fb_provider, fb_model in await self._resolve_fallback_candidates(provider_name, model):
            fb = self.get_provider(fb_provider)
            if not fb:
                continue
            try:
                logger.info(f"Fallback a {fb_provider}:{fb_model}")
                self._set_last_generation_meta(
                    provider=fb_provider,
                    model=fb_model,
                    requested_provider=provider_name,
                    requested_model=model,
                    fallback=True,
                )
                async for chunk in fb.generate(
                    messages, fb_model, temperature, max_tokens, stream, **kwargs
                ):
                    yield chunk
                return
            except Exception as exc:
                logger.warning(f"Fallback {fb_provider} tambien fallo: {exc}")

        providers_tried = [provider_name] + [
            fb_p for fb_p, _ in await self._resolve_fallback_candidates(provider_name, model)
        ]
        raise LLMProviderUnavailableError(
            providers_tried=providers_tried,
            last_error="Verifica tus API keys en Settings.",
        )

    async def _get_local_model(self, provider_name: str) -> str | None:
        """Obtiene el primer modelo disponible de un provider local."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None
        try:
            models = await provider.list_models()
            if models:
                return models[0]
        except Exception:
            pass
        defaults = {"ollama": "llama3", "lmstudio": "default"}
        return defaults.get(provider_name)

    async def generate_complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        provider_name: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Non-streaming con fallback."""
        if model is None:
            model = self.get_current_model()
        if provider_name is None:
            provider_name = self.get_current_provider_name()

        # Validar que el modelo soporte generateContent (no sea live-only)
        self._validate_model_for_text_chat(provider_name, model)

        provider = self.get_provider(provider_name)
        if provider:
            try:
                response = await provider.generate_complete(messages, model, **kwargs)
                self._set_last_generation_meta(
                    provider=response.provider or provider_name,
                    model=response.model or model,
                    requested_provider=provider_name,
                    requested_model=model,
                    fallback=False,
                )
                return response
            except Exception as exc:
                logger.warning(f"Provider {provider_name} fallo: {exc}")

        for fb_provider, fb_model in await self._resolve_fallback_candidates(provider_name, model):
            fb = self.get_provider(fb_provider)
            if not fb:
                continue
            try:
                logger.info(f"Fallback complete a {fb_provider}:{fb_model}")
                response = await fb.generate_complete(messages, fb_model, **kwargs)
                self._set_last_generation_meta(
                    provider=response.provider or fb_provider,
                    model=response.model or fb_model,
                    requested_provider=provider_name,
                    requested_model=model,
                    fallback=True,
                )
                return response
            except Exception as exc:
                logger.warning(f"Fallback complete {fb_provider} tambien fallo: {exc}")

        providers_tried = [provider_name or "none"] + [
            fb_p for fb_p, _ in await self._resolve_fallback_candidates(provider_name or "none", model)
        ]
        raise LLMProviderUnavailableError(
            providers_tried=providers_tried,
            last_error="Ningun provider respondio tras fallback.",
        )

    async def list_all_models(self) -> dict[str, list[str]]:
        """Lista todos los modelos de todos los providers."""
        result = {}
        for name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                if models:
                    result[name] = models
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------
    # Cost-aware routing (Fase 9.4)
    # ------------------------------------------------------------------

    async def generate_cost_aware(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        provider_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        session_id: str = "",
        mode_key: str = "",
        source: str = "agent_loop_stream",
        estimated_input_tokens: int = 0,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta aplicando optimizacion de costos automatica.
        Evalua presion presupuestaria y decide si conviene cambiar de modelo.
        Retorna el mismo flujo que generate(), pero puede usar un modelo distinto.
        """
        if model is None:
            model = self.get_current_model()
        if provider_name is None:
            provider_name = self.get_current_provider_name()

        final_provider = provider_name
        final_model = model
        optimization: Any = None

        try:
            from backend.core.cost_optimizer import get_cost_optimizer
            optimizer = get_cost_optimizer()
            optimization = await optimizer.resolve_model(
                requested_provider=provider_name,
                requested_model=model,
                session_id=session_id,
                mode_key=mode_key,
                source=source,
                estimated_input_tokens=estimated_input_tokens,
            )
            if optimization.switched:
                final_provider = optimization.provider
                final_model = optimization.model
                logger.info(
                    f"CostOptimizer switch: {provider_name}:{model} → "
                    f"{final_provider}:{final_model} ({optimization.reason})"
                )
        except Exception as exc:
            logger.debug(f"CostOptimizer no disponible, usando modelo original: {exc}")

        # Almacenar la info de optimizacion en los metadatos de la generacion
        self._last_optimization = optimization

        async for chunk in self.generate(
            messages,
            model=final_model,
            provider_name=final_provider,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs,
        ):
            yield chunk

    async def generate_complete_cost_aware(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        provider_name: str | None = None,
        session_id: str = "",
        mode_key: str = "",
        source: str = "agent_loop_complete",
        estimated_input_tokens: int = 0,
        **kwargs,
    ) -> LLMResponse:
        """Non-streaming cost-aware generation."""
        if model is None:
            model = self.get_current_model()
        if provider_name is None:
            provider_name = self.get_current_provider_name()

        final_provider = provider_name
        final_model = model

        try:
            from backend.core.cost_optimizer import get_cost_optimizer
            optimizer = get_cost_optimizer()
            optimization = await optimizer.resolve_model(
                requested_provider=provider_name,
                requested_model=model,
                session_id=session_id,
                mode_key=mode_key,
                source=source,
                estimated_input_tokens=estimated_input_tokens,
            )
            if optimization.switched:
                final_provider = optimization.provider
                final_model = optimization.model
                logger.info(
                    f"CostOptimizer switch (complete): {provider_name}:{model} → "
                    f"{final_provider}:{final_model} ({optimization.reason})"
                )
            self._last_optimization = optimization
        except Exception as exc:
            logger.debug(f"CostOptimizer (complete) no disponible: {exc}")

        return await self.generate_complete(
            messages, model=final_model, provider_name=final_provider, **kwargs
        )

    def get_last_optimization(self) -> Any:
        """Retorna la ultima decision de optimizacion, o None."""
        return getattr(self, "_last_optimization", None)
