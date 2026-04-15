"""
G-Mini Agent — Visual Verifier.
Verificador visual de acciones empleando capturas de pantalla rápidas.
"""

import asyncio
import base64
import time
import json
from typing import Any
import mss
import mss.tools
from loguru import logger

from backend.providers.router import ModelRouter
from backend.providers.base import LLMMessage

class VisualVerifier:
    """
    Verificador visual de acciones.
    Toma capturas ultra-rápidas con mss y usa ModelRouter para verificar visualmente un estado esperado.
    """

    def __init__(self):
        self.router = ModelRouter()

    async def verify_action(self, action_description: str, expected_state: str, timeout: float = 3.0) -> dict[str, Any]:
        """
        Captura la pantalla actual y usa el LLM para determinar si el resultado esperado se logró tras la acción.
        """
        start_time = time.time()
        attempt = 1
        
        while time.time() - start_time < timeout:
            try:
                # Captura rápida usando mss
                with mss.mss() as sct:
                    # Intentar usar el monitor principal
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                    b64_img = base64.b64encode(img_bytes).decode('utf-8')
                
                # Armar prompt de verificación
                prompt = (
                    f"Acabo de ejecutar esta acción: '{action_description}'. "
                    f"Verifica si se logró el siguiente estado en pantalla: '{expected_state}'. "
                    "Responde únicamente con un JSON de este formato: "
                    '{"success": true|false, "reason": "breve justificación"}'
                )
                
                messages = [
                    LLMMessage(
                        role="system", 
                        content="Eres un evaluador visual estricto de UI. Analiza la pantalla y el estado, y responde solo con JSON."
                    ),
                    LLMMessage(
                        role="user",
                        content=[
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                        ]
                    )
                ]
                
                # Obtener el modelo y consultar al router en modo JSON estructurado
                model = self.router.get_current_model() or "gpt-4o"
                response = await self.router.generate_complete(
                    messages=messages,
                    model=model,
                    response_format={"type": "json_object"}
                )
                
                try:
                    result = json.loads(response)
                    if result.get("success"):
                        return {
                            "success": True,
                            "reason": result.get("reason", "Estado visual verificado correctamente."),
                            "attempts": attempt
                        }
                    else:
                        logger.debug(f"Verificación visual falló (intento {attempt}): {result.get('reason')}")
                except json.JSONDecodeError:
                    logger.warning(f"Respuesta JSON del verificador inválida: {response}")
                    
            except Exception as e:
                logger.error(f"Error en VisualVerifier durante el intento {attempt}: {e}")
                
            attempt += 1
            await asyncio.sleep(1.0)
            
        return {
            "success": False,
            "reason": "Se agotó el tiempo de espera esperando que se cumpla la condición visual.",
            "attempts": attempt
        }
