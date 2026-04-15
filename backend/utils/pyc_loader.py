"""Compatibility helpers for loading retained CPython bytecode modules."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import re
import sys
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any, MutableMapping

_CACHE_TAG_PATTERN = re.compile(r"\.(?P<tag>[^.]+)\.pyc$")


def _extract_cache_tag(filename: str) -> str:
    match = _CACHE_TAG_PATTERN.search(filename)
    if not match:
        raise ImportError(f"No se pudo extraer cache tag desde {filename!r}")
    return match.group("tag")


def load_private_pyc_module(
    public_module_name: str,
    pyc_path: str | PathLike[str],
) -> ModuleType:
    """Load a retained `.pyc` file under a private alias."""
    pyc_path = Path(pyc_path).resolve()
    if not pyc_path.is_file():
        raise ImportError(
            f"No se encontro el bytecode requerido para {public_module_name}: {pyc_path}"
        )

    runtime_tag = sys.implementation.cache_tag or ""
    bytecode_tag = _extract_cache_tag(pyc_path.name)
    if runtime_tag != bytecode_tag:
        raise ImportError(
            f"Bytecode incompatible para {public_module_name}: "
            f"runtime={runtime_tag or '?'} bytecode={bytecode_tag}"
        )

    alias = (
        f"_gmini_compat_{public_module_name.replace('.', '_')}_"
        f"{runtime_tag.replace('-', '_')}"
    )
    cached_module = sys.modules.get(alias)
    if isinstance(cached_module, ModuleType):
        return cached_module

    loader = importlib.machinery.SourcelessFileLoader(alias, str(pyc_path))
    spec = importlib.util.spec_from_loader(alias, loader)
    if spec is None:
        raise ImportError(f"No se pudo crear spec para {public_module_name} desde {pyc_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    try:
        loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(alias, None)
        raise ImportError(
            f"No se pudo cargar {public_module_name} desde bytecode retenido: {pyc_path}"
        ) from exc
    return module


def reexport_public(
    module: ModuleType,
    namespace: MutableMapping[str, Any],
    public_module_name: str,
) -> list[str]:
    """Copy public attributes from a loaded compatibility module into a wrapper."""
    exported: list[str] = []
    for name in dir(module):
        if name.startswith("_"):
            continue
        value = getattr(module, name)
        namespace[name] = value
        exported.append(name)
        if getattr(value, "__module__", None) == module.__name__:
            try:
                value.__module__ = public_module_name
            except Exception:
                pass
    return exported
