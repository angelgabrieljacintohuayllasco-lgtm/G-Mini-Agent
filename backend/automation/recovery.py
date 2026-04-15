"""
G-Mini Agent — Local Recovery Manager.
Gestor de recuperación local en caso de fallos.
"""

import asyncio
from typing import Any
from loguru import logger
from backend.automation.pc_controller import AutomationEngine

class LocalRecoveryManager:
    """
    Gestor de recuperación local.
    Analiza el tipo de acción que falló y ejecuta medidas correctivas con AutomationEngine 
    (scrolls, movimiento de mouse, escapes) antes de un reintento.
    """

    def __init__(self, engine: AutomationEngine | None = None):
        self.engine = engine or AutomationEngine()
        self._engine_owned = engine is None

    async def attempt_recovery(self, failed_action: str, context: dict[str, Any] | None = None) -> bool:
        """
        Intenta recuperar el sistema según el tipo de acción que acaba de fallar.
        Retorna True si se aplicó una medida de recuperación.
        """
        logger.warning(f"Intentando recuperación local para la acción: {failed_action}")

        try:
            # Solo inicializar si el engine es propio (no reutilizado del planner)
            if self._engine_owned and hasattr(self.engine, "initialize"):
                await self.engine.initialize()

            if failed_action in ("click", "double_click", "right_click", "browser_click", "desktop_click"):
                logger.info("Recuperación: Acción de click falló. Realizando scroll para revelar contenido...")
                await self.engine.scroll(clicks=-300)
                await asyncio.sleep(1.0)
                return True

            elif failed_action in ("type", "focus_type", "browser_type", "desktop_type"):
                logger.info("Recuperación: Acción de escritura falló. Presionando Escape para limpiar foco...")
                await self.engine.hotkey("esc")
                await asyncio.sleep(0.5)
                return True

            elif failed_action in ("locate", "vision_locate", "screen_find"):
                logger.info("Recuperación: No se pudo localizar. Desplazando el mouse al centro para limpiar tooltips...")
                await self.engine.move_to(x=500, y=500, duration=0.2)
                await asyncio.sleep(0.5)
                return True

            elif failed_action in ("scroll",):
                logger.info("Recuperación: Scroll falló. Moviendo mouse al centro de pantalla...")
                await self.engine.move_to(x=960, y=540, duration=0.2)
                await asyncio.sleep(0.3)
                return True

            elif failed_action in ("drag",):
                logger.info("Recuperación: Drag falló. Presionando Escape y soltando mouse...")
                await self.engine.hotkey("esc")
                await self.engine.move_to(x=0, y=0, duration=0.1)
                await asyncio.sleep(0.5)
                return True

            elif failed_action in ("press", "key", "hotkey"):
                logger.info("Recuperación: Tecla falló. Esperando estabilización...")
                await asyncio.sleep(0.5)
                return True

            elif failed_action in ("move",):
                logger.info("Recuperación: Move falló. Esperando estabilización...")
                await asyncio.sleep(0.3)
                return True

            elif failed_action in ("browser_navigate", "browser_open", "browser_go"):
                logger.info("Recuperación: Navegación browser falló. Presionando Escape para cancelar carga...")
                await self.engine.hotkey("esc")
                await asyncio.sleep(0.5)
                return True

            elif failed_action in ("browser_press", "browser_hotkey"):
                logger.info("Recuperación: Tecla browser falló. Presionando Escape para limpiar estado...")
                await self.engine.hotkey("esc")
                await asyncio.sleep(0.3)
                return True

            else:
                logger.info("Recuperación genérica: Pausando para estabilización de UI...")
                await asyncio.sleep(1.5)
                return True

        except Exception as e:
            logger.error(f"Fallo durante la ejecución de LocalRecoveryManager: {e}")
            return False
