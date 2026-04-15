"""G-Mini Agent — Logger centralizado con loguru."""

import sys
from pathlib import Path

from loguru import logger

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Remover handler default
logger.remove()

# Consola con colores
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> — <level>{message}</level>",
    level="DEBUG",
    colorize=True,
)

# Archivo rotativo
logger.add(
    LOG_DIR / "gmini_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
    level="DEBUG",
    encoding="utf-8",
)
