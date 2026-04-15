"""
G-Mini Agent — UI Detector.
Detección de elementos de interfaz usando YOLO/OmniParser.
Identifica botones, campos de texto, iconos, menús, etc.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from backend.config import config


@dataclass
class UIElement:
    """Elemento de UI detectado en pantalla."""
    type: str  # button, text_field, icon, menu, checkbox, link, label
    text: str  # Texto contenido
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float  # 0.0 - 1.0
    center: tuple[int, int] = (0, 0)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        x1, y1, x2, y2 = self.bbox
        self.center = ((x1 + x2) // 2, (y1 + y2) // 2)


class UIDetector:
    """
    Detección de elementos de UI en capturas de pantalla.
    Usa detección heurística básica (Fase 2 inicial) 
    con soporte para OmniParser/YOLO en versiones avanzadas.
    """

    def __init__(self):
        self._model = None
        self._model_type: str = "heuristic"
        self._initialized = False

    async def initialize(self) -> None:
        """Intenta cargar el modelo de detección."""
        detector_type = config.get("vision", "ui_detector", default="heuristic")

        if detector_type == "omniparser":
            try:
                await self._init_omniparser()
            except Exception as e:
                logger.warning(f"OmniParser no disponible: {e}. Usando heurístico.")

        self._initialized = True
        logger.info(f"UIDetector inicializado (modo: {self._model_type})")

    async def _init_omniparser(self) -> None:
        """Inicializa OmniParser (Microsoft) para detección de UI."""
        try:
            from ultralytics import YOLO
            model_path = config.get("vision", "omniparser_model", default="")
            if model_path:
                self._model = YOLO(model_path)
                self._model_type = "omniparser"
                logger.info("OmniParser YOLO cargado")
        except ImportError:
            raise ImportError("ultralytics no instalado")

    async def detect_elements(
        self,
        image_bytes: bytes,
    ) -> list[UIElement]:
        """
        Detecta elementos de UI en una imagen.
        Retorna lista de UIElement con tipo, posición y texto.
        """
        if not HAS_PIL:
            return []

        start = time.perf_counter()

        if self._model_type == "omniparser" and self._model:
            elements = await self._detect_yolo(image_bytes)
        else:
            elements = await self._detect_heuristic(image_bytes)

        elapsed = (time.perf_counter() - start) * 1000
        logger.debug(f"UI Detection: {len(elements)} elementos en {elapsed:.1f}ms")

        return elements

    async def _detect_yolo(self, image_bytes: bytes) -> list[UIElement]:
        """Detección con YOLO/OmniParser."""
        import asyncio
        import numpy as np

        img = Image.open(io.BytesIO(image_bytes))
        img_np = np.array(img)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, self._model, img_np)

        elements = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls_id = int(box.cls[0].item())
                cls_name = result.names.get(cls_id, "unknown")

                elements.append(UIElement(
                    type=cls_name,
                    text="",
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    confidence=conf,
                ))

        return elements

    async def _detect_heuristic(self, image_bytes: bytes) -> list[UIElement]:
        """
        Detección heurística básica.
        Busca regiones con bordes definidos que podrían ser botones/campos.
        Esta es una implementación placeholder — suficiente para que el agente
        pueda operar con OCR + coordenadas generales.
        """
        # En modo heurístico, confiamos más en OCR + LLM para interpretar
        # la posición de los elementos. El LLM recibe la imagen y pide
        # hacer clic en coordenadas específicas.
        return []

    def describe_elements(self, elements: list[UIElement]) -> str:
        """
        Genera una descripción textual de los elementos detectados.
        Útil para el modo Token Saver.
        """
        if not elements:
            return "No se detectaron elementos de UI."

        lines = ["Elementos de UI detectados:"]
        for i, el in enumerate(elements, 1):
            x, y = el.center
            lines.append(
                f"  [{i}] {el.type}: \"{el.text}\" en ({x}, {y}) "
                f"[confianza: {el.confidence:.0%}]"
            )

        return "\n".join(lines)
