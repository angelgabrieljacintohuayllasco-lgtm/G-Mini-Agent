"""Compatibility wrapper for the retained resilience bytecode."""

from __future__ import annotations

from pathlib import Path

from backend.utils.pyc_loader import load_private_pyc_module, reexport_public

_legacy = load_private_pyc_module(
    __name__,
    Path(__file__).resolve().with_name("__pycache__")
    / "resilience.retained.cpython-313.pyc",
)

__all__ = reexport_public(_legacy, globals(), __name__)
