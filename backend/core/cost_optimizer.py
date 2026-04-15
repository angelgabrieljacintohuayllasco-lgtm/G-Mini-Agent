"""
G-Mini Agent — Optimizador de costos LLM.

Auto-switch a modelos mas economicos segun presion presupuestaria,
compresion de contexto antes de llamadas costosas, y priorizacion
de modelos locales para tareas no criticas.

Fase 9.4 del roadmap.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from backend.config import config


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CRITICALITY_CRITICAL = "critical"
CRITICALITY_STANDARD = "standard"
CRITICALITY_LOW = "low"

PRESSURE_NONE = "none"
PRESSURE_LOW = "low"
PRESSURE_MEDIUM = "medium"
PRESSURE_HIGH = "high"
PRESSURE_EXCEEDED = "exceeded"

# Fuentes que siempre merecen el modelo configurado por el usuario
_CRITICAL_SOURCES = frozenset({
    "agent_loop_stream",
    "agent_loop_complete",
    "critic",
    "critic_gate",
})

# Fuentes internas que pueden funcionar bien con modelos baratos
_LOW_CRITICALITY_SOURCES = frozenset({
    "delegation_planner",
    "session_compressor",
    "summary_generator",
    "tag_extractor",
    "auto_classifier",
    "stagnation_detector",
    "action_feedback",
    "knowledge_graph_extract",
    "weekly_report",
})

# Modelos locales (costo 0) reconocidos por provider
_LOCAL_PROVIDERS = frozenset({"ollama", "lmstudio"})


# ---------------------------------------------------------------------------
# Dataclass de resultado de optimizacion
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationResult:
    """Resultado de la decision de optimizacion de costos."""

    provider: str
    model: str
    original_provider: str
    original_model: str
    switched: bool
    reason: str
    pressure_level: str
    criticality: str
    compress_context: bool
    estimated_savings_percent: float = 0.0


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class CostOptimizer:
    """
    Optimizador de costos que intercepta la seleccion de modelo en el router
    y decide si conviene hacer downgrade, usar un modelo local o comprimir contexto.
    """

    def __init__(self) -> None:
        self._last_pressure_check: float = 0.0
        self._cached_pressure: dict[str, Any] = {}
        self._pressure_cache_ttl: float = 10.0  # segundos
        self._switch_count: int = 0

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_enabled() -> bool:
        return bool(config.get("cost_optimization", "enabled", default=False))

    @staticmethod
    def _downgrade_chain() -> list[dict[str, str]]:
        """Cadena ordenada de modelos de menor a mayor costo para downgrade."""
        raw = config.get("cost_optimization", "downgrade_chain", default=[]) or []
        if not isinstance(raw, list):
            return []
        chain: list[dict[str, str]] = []
        for entry in raw:
            if isinstance(entry, dict) and entry.get("provider") and entry.get("model"):
                chain.append({
                    "provider": str(entry["provider"]).strip(),
                    "model": str(entry["model"]).strip(),
                })
            elif isinstance(entry, str) and ":" in entry:
                parts = entry.split(":", 1)
                chain.append({
                    "provider": parts[0].strip(),
                    "model": parts[1].strip(),
                })
        return chain

    @staticmethod
    def _local_fallback() -> dict[str, str] | None:
        provider = str(config.get("cost_optimization", "local_fallback_provider", default="") or "").strip()
        model = str(config.get("cost_optimization", "local_fallback_model", default="") or "").strip()
        if provider:
            return {"provider": provider, "model": model}
        return None

    @staticmethod
    def _pressure_thresholds() -> dict[str, float]:
        return {
            "medium": float(config.get("cost_optimization", "pressure_threshold_medium", default=60.0) or 60.0),
            "high": float(config.get("cost_optimization", "pressure_threshold_high", default=80.0) or 80.0),
        }

    @staticmethod
    def _compression_token_threshold() -> int:
        return int(config.get("cost_optimization", "compress_context_above_tokens", default=40000) or 40000)

    @staticmethod
    def _pricing_table() -> dict[str, dict[str, Any]]:
        raw = config.get("budget", "model_pricing", default={}) or {}
        if not isinstance(raw, dict):
            return {}
        return {
            str(k).strip().lower(): v
            for k, v in raw.items()
            if isinstance(v, dict)
        }

    # ------------------------------------------------------------------
    # Clasificacion de criticidad
    # ------------------------------------------------------------------

    def classify_criticality(self, source: str, mode_key: str) -> str:
        """
        Clasifica la criticidad de una llamada LLM segun su fuente y modo.
        - critical: el usuario ve el resultado directamente, o es una decision de seguridad
        - standard: tarea normal del agente
        - low: tarea interna, planificacion, clasificacion, extraccion
        """
        source_lower = str(source or "").strip().lower()
        mode_lower = str(mode_key or "").strip().lower()

        if source_lower in _CRITICAL_SOURCES:
            return CRITICALITY_CRITICAL

        if source_lower in _LOW_CRITICALITY_SOURCES:
            return CRITICALITY_LOW

        # Modos de alto impacto siempre son standard minimo
        if mode_lower in {"pentester", "programador"}:
            return CRITICALITY_STANDARD

        # Sub-agentes bajan un escalon
        if "subagent" in source_lower or "worker" in source_lower:
            return CRITICALITY_LOW

        return CRITICALITY_STANDARD

    # ------------------------------------------------------------------
    # Calculo de presion presupuestaria
    # ------------------------------------------------------------------

    async def get_budget_pressure(
        self,
        session_id: str,
        mode_key: str,
    ) -> dict[str, Any]:
        """
        Calcula la presion presupuestaria actual.
        Retorna nivel y metricas detalladas.
        """
        now = time.monotonic()
        cache_key = f"{session_id}:{mode_key}"
        if (
            self._cached_pressure.get("_key") == cache_key
            and (now - self._last_pressure_check) < self._pressure_cache_ttl
        ):
            return self._cached_pressure

        from backend.core.cost_tracker import get_cost_tracker

        tracker = get_cost_tracker()
        await tracker.initialize()

        summary = await tracker.get_summary(
            session_id=session_id,
            current_mode=mode_key,
        )

        budget_status = summary.get("budget_status", {})
        thresholds = self._pressure_thresholds()

        # Calcular presion como el maximo de todos los buckets activos
        max_usage_percent = 0.0
        active_scopes: list[dict[str, Any]] = []

        for scope_name in ("session", "daily", "monthly", "mode"):
            scope = budget_status.get(scope_name, {})
            if scope.get("state") == "unlimited":
                continue
            usage_pct = float(scope.get("usage_percent", 0.0))
            active_scopes.append({
                "scope": scope_name,
                "usage_percent": usage_pct,
                "state": scope.get("state", "ok"),
                "remaining_usd": scope.get("remaining_usd"),
                "limit_usd": scope.get("limit_usd", 0.0),
            })
            if usage_pct > max_usage_percent:
                max_usage_percent = usage_pct

        # Determinar nivel de presion
        if budget_status.get("stop_required"):
            level = PRESSURE_EXCEEDED
        elif max_usage_percent >= thresholds["high"]:
            level = PRESSURE_HIGH
        elif max_usage_percent >= thresholds["medium"]:
            level = PRESSURE_MEDIUM
        elif max_usage_percent > 0:
            level = PRESSURE_LOW
        else:
            level = PRESSURE_NONE

        result = {
            "_key": cache_key,
            "level": level,
            "max_usage_percent": round(max_usage_percent, 2),
            "scopes": active_scopes,
            "stop_required": bool(budget_status.get("stop_required")),
            "alerts": budget_status.get("alerts", []),
            "checked_at": time.time(),
        }
        self._cached_pressure = result
        self._last_pressure_check = now
        return result

    # ------------------------------------------------------------------
    # Costos por modelo
    # ------------------------------------------------------------------

    def _model_cost_per_million(self, model: str) -> float:
        """Costo combinado (input + output) por millon de tokens."""
        table = self._pricing_table()
        model_key = str(model or "").strip().lower()
        pricing = table.get(model_key, {})
        return float(pricing.get("input_per_million_usd", 0)) + float(pricing.get("output_per_million_usd", 0))

    def _find_cheaper_model(
        self,
        current_provider: str,
        current_model: str,
        max_criticality: str,
    ) -> dict[str, str] | None:
        """
        Busca un modelo mas economico en la cadena de downgrade
        que sea apropiado para el nivel de criticidad dado.
        """
        current_cost = self._model_cost_per_million(current_model)
        if current_cost <= 0:
            return None  # El modelo actual ya es gratuito o desconocido

        chain = self._downgrade_chain()
        if not chain:
            return None

        best: dict[str, str] | None = None
        best_cost = current_cost

        for candidate in chain:
            candidate_model = candidate["model"]
            candidate_cost = self._model_cost_per_million(candidate_model)

            # Solo considerar modelos mas baratos
            if candidate_cost >= best_cost:
                continue

            # Para tareas criticas, no bajar mas del 50% del costo original
            if max_criticality == CRITICALITY_CRITICAL and candidate_cost < current_cost * 0.5:
                continue

            best = candidate
            best_cost = candidate_cost

        return best

    # ------------------------------------------------------------------
    # Decision principal de optimizacion
    # ------------------------------------------------------------------

    async def resolve_model(
        self,
        *,
        requested_provider: str,
        requested_model: str,
        session_id: str,
        mode_key: str,
        source: str,
        estimated_input_tokens: int = 0,
    ) -> OptimizationResult:
        """
        Decide si se debe cambiar el modelo / provider para optimizar costos.

        Logica:
        1. Si no esta habilitado, devuelve el modelo solicitado sin cambios.
        2. Clasifica la criticidad de la tarea.
        3. Evalua la presion presupuestaria.
        4. Si hay presion alta y la tarea es de baja criticidad → local o downgrade.
        5. Si hay presion media → downgrade moderado.
        6. Evalua si comprimir contexto antes de la llamada.
        """
        orig_provider = str(requested_provider or "").strip()
        orig_model = str(requested_model or "").strip()

        no_switch = OptimizationResult(
            provider=orig_provider,
            model=orig_model,
            original_provider=orig_provider,
            original_model=orig_model,
            switched=False,
            reason="",
            pressure_level=PRESSURE_NONE,
            criticality=CRITICALITY_STANDARD,
            compress_context=False,
        )

        if not self._is_enabled():
            return no_switch

        # Ya es un provider local → no hay nada que optimizar
        if orig_provider in _LOCAL_PROVIDERS:
            return no_switch

        criticality = self.classify_criticality(source, mode_key)

        try:
            pressure = await self.get_budget_pressure(session_id, mode_key)
        except Exception as exc:
            logger.debug(f"CostOptimizer: no pudo evaluar presion: {exc}")
            return no_switch

        pressure_level = pressure.get("level", PRESSURE_NONE)

        # Decidir si comprimir contexto
        compress = False
        token_threshold = self._compression_token_threshold()
        if estimated_input_tokens > 0 and estimated_input_tokens > token_threshold:
            # Comprimir si tokens altos Y presion al menos media
            if pressure_level in (PRESSURE_MEDIUM, PRESSURE_HIGH, PRESSURE_EXCEEDED):
                compress = True
            # Siempre comprimir si excede 2x el threshold
            elif estimated_input_tokens > token_threshold * 2:
                compress = True

        # Sin presion → sin cambio de modelo
        if pressure_level in (PRESSURE_NONE, PRESSURE_LOW):
            return OptimizationResult(
                provider=orig_provider,
                model=orig_model,
                original_provider=orig_provider,
                original_model=orig_model,
                switched=False,
                reason="presion baja, manteniendo modelo configurado",
                pressure_level=pressure_level,
                criticality=criticality,
                compress_context=compress,
            )

        # Presion alta/exceeded → priorizar local para tareas no criticas
        if pressure_level in (PRESSURE_HIGH, PRESSURE_EXCEEDED) and criticality == CRITICALITY_LOW:
            local = self._local_fallback()
            if local:
                self._switch_count += 1
                logger.info(
                    f"CostOptimizer: switch a local {local['provider']}:{local['model']} "
                    f"(presion={pressure_level}, criticidad={criticality}, fuente={source})"
                )
                return OptimizationResult(
                    provider=local["provider"],
                    model=local["model"],
                    original_provider=orig_provider,
                    original_model=orig_model,
                    switched=True,
                    reason=f"presion {pressure_level}: priorizar modelo local para tarea {criticality}",
                    pressure_level=pressure_level,
                    criticality=criticality,
                    compress_context=compress,
                    estimated_savings_percent=100.0,
                )

        # Presion media/alta → buscar downgrade en cadena
        if pressure_level in (PRESSURE_MEDIUM, PRESSURE_HIGH, PRESSURE_EXCEEDED):
            cheaper = self._find_cheaper_model(orig_provider, orig_model, criticality)
            if cheaper:
                orig_cost = self._model_cost_per_million(orig_model)
                new_cost = self._model_cost_per_million(cheaper["model"])
                savings = round(((orig_cost - new_cost) / orig_cost) * 100.0, 1) if orig_cost > 0 else 0.0

                self._switch_count += 1
                logger.info(
                    f"CostOptimizer: downgrade {orig_provider}:{orig_model} → "
                    f"{cheaper['provider']}:{cheaper['model']} "
                    f"(ahorro={savings}%, presion={pressure_level}, criticidad={criticality})"
                )
                return OptimizationResult(
                    provider=cheaper["provider"],
                    model=cheaper["model"],
                    original_provider=orig_provider,
                    original_model=orig_model,
                    switched=True,
                    reason=f"presion {pressure_level}: downgrade para tarea {criticality} (ahorro ~{savings}%)",
                    pressure_level=pressure_level,
                    criticality=criticality,
                    compress_context=compress,
                    estimated_savings_percent=savings,
                )

        # Sin candidatos de downgrade, al menos reportar el estado
        return OptimizationResult(
            provider=orig_provider,
            model=orig_model,
            original_provider=orig_provider,
            original_model=orig_model,
            switched=False,
            reason=f"presion {pressure_level} pero sin candidatos de downgrade disponibles",
            pressure_level=pressure_level,
            criticality=criticality,
            compress_context=compress,
        )

    # ------------------------------------------------------------------
    # Estado / estadisticas
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Estado actual del optimizador para UI / API."""
        return {
            "enabled": self._is_enabled(),
            "total_switches": self._switch_count,
            "last_pressure": {
                k: v for k, v in self._cached_pressure.items() if k != "_key"
            } if self._cached_pressure else None,
            "downgrade_chain_size": len(self._downgrade_chain()),
            "local_fallback_configured": self._local_fallback() is not None,
            "compression_token_threshold": self._compression_token_threshold(),
        }

    def invalidate_cache(self) -> None:
        """Fuerza recalculo de presion en la siguiente llamada."""
        self._cached_pressure = {}
        self._last_pressure_check = 0.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_cost_optimizer: CostOptimizer | None = None


def get_cost_optimizer() -> CostOptimizer:
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer()
    return _cost_optimizer
