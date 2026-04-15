"""
G-Mini Agent — ADB Controller.
Control de dispositivos Android via ADB (Android Debug Bridge).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from loguru import logger

try:
    from ppadb.client import Client as AdbClient
    HAS_ADB = True
except ImportError:
    HAS_ADB = False
    logger.info("pure-python-adb no disponible — control Android deshabilitado")

from backend.config import config


class ADBController:
    """
    Control de dispositivos Android via ADB.
    - Tap, swipe, texto
    - Captura de pantalla
    - Instalación de APKs
    - Shell commands
    """

    def __init__(self):
        self._client: Any = None
        self._device: Any = None
        self._connected = False

    async def initialize(self) -> None:
        """Intenta conectar al servidor ADB."""
        if not HAS_ADB:
            logger.info("ADB no disponible")
            return

        host = config.get("adb", "host", default="127.0.0.1")
        port = config.get("adb", "port", default=5037)

        try:
            self._client = AdbClient(host=host, port=port)
            devices = self._client.devices()

            if devices:
                self._device = devices[0]
                self._connected = True
                logger.info(f"ADB conectado: {self._device.serial}")
            else:
                logger.info("ADB: No hay dispositivos conectados")

        except Exception as e:
            logger.debug(f"ADB no disponible: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _check_connected(self) -> bool:
        if not self._connected or not self._device:
            logger.warning("No hay dispositivo Android conectado")
            return False
        return True

    async def tap(self, x: int, y: int) -> bool:
        """Tap en coordenadas."""
        if not self._check_connected():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._device.shell(f"input tap {x} {y}")
            )
            logger.debug(f"ADB tap: ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"ADB tap error: {e}")
            return False

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe de (x1,y1) a (x2,y2)."""
        if not self._check_connected():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}"),
            )
            logger.debug(f"ADB swipe: ({x1},{y1}) → ({x2},{y2})")
            return True
        except Exception as e:
            logger.error(f"ADB swipe error: {e}")
            return False

    async def input_text(self, text: str) -> bool:
        """Escribe texto (escapando caracteres especiales)."""
        if not self._check_connected():
            return False

        try:
            escaped = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._device.shell(f"input text '{escaped}'")
            )
            return True
        except Exception as e:
            logger.error(f"ADB text error: {e}")
            return False

    async def press_key(self, keycode: int) -> bool:
        """Presiona una tecla por keycode (ej: 3=HOME, 4=BACK, 66=ENTER)."""
        if not self._check_connected():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._device.shell(f"input keyevent {keycode}")
            )
            return True
        except Exception as e:
            logger.error(f"ADB keyevent error: {e}")
            return False

    async def screenshot(self) -> bytes | None:
        """Captura pantalla del dispositivo Android como PNG bytes."""
        if not self._check_connected():
            return None

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self._device.screencap()
            )
            return result
        except Exception as e:
            logger.error(f"ADB screenshot error: {e}")
            return None

    async def shell(self, command: str) -> str:
        """Ejecuta un comando shell en el dispositivo."""
        if not self._check_connected():
            return ""

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self._device.shell(command)
            )
            return result or ""
        except Exception as e:
            logger.error(f"ADB shell error: {e}")
            return ""

    async def list_devices(self) -> list[str]:
        """Lista dispositivos ADB conectados."""
        if not self._client:
            return []

        try:
            devices = self._client.devices()
            return [d.serial for d in devices]
        except Exception:
            return []
