"""
browser-control skill — Control del navegador Chrome via backend API.
Envía comandos al extension bridge de G-Mini Agent vía REST.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any

BACKEND_URL = os.environ.get("GMINI_BACKEND_URL", "http://localhost:8765")


def _load_payload() -> dict[str, Any]:
    path = os.environ.get("GMINI_SKILL_INPUT")
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(sys.stdin.read() or "{}")


def _write_output(data: dict[str, Any]) -> None:
    out_path = os.environ.get("GMINI_SKILL_OUTPUT")
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


def _backend_action(action_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta una acción del browser vía el endpoint /actions/execute del backend."""
    url = f"{BACKEND_URL}/actions/execute"
    body = json.dumps({
        "actions": [{"type": action_type, "params": params}],
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def tool_browser_navigate(payload: dict[str, Any]) -> dict[str, Any]:
    url_target = payload.get("url", "").strip()
    if not url_target:
        return {"error": "Se requiere 'url'"}
    return _backend_action("browser_navigate", {"url": url_target})


def tool_browser_click(payload: dict[str, Any]) -> dict[str, Any]:
    selector = payload.get("selector", "").strip()
    if not selector:
        return {"error": "Se requiere 'selector'"}
    return _backend_action("browser_click", {"selector": selector})


def tool_browser_type(payload: dict[str, Any]) -> dict[str, Any]:
    selector = payload.get("selector", "").strip()
    text = payload.get("text", "")
    if not selector:
        return {"error": "Se requiere 'selector'"}
    return _backend_action("browser_type", {"selector": selector, "text": text})


def tool_browser_extract(payload: dict[str, Any]) -> dict[str, Any]:
    selector = payload.get("selector", "body")
    return _backend_action("browser_extract", {"selector": selector})


def tool_browser_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return _backend_action("browser_snapshot", {})


def tool_browser_eval(payload: dict[str, Any]) -> dict[str, Any]:
    script = payload.get("script", "").strip()
    if not script:
        return {"error": "Se requiere 'script'"}
    return _backend_action("browser_eval", {"script": script})


def tool_browser_get_dom(payload: dict[str, Any]) -> dict[str, Any]:
    selector = payload.get("selector", "body")
    max_depth = int(payload.get("max_depth", 6))
    max_length = int(payload.get("max_length", 12000))
    return _backend_action("browser_get_dom", {
        "selector": selector,
        "max_depth": max_depth,
        "max_length": max_length,
    })


TOOLS = {
    "browser_navigate": tool_browser_navigate,
    "browser_click": tool_browser_click,
    "browser_type": tool_browser_type,
    "browser_extract": tool_browser_extract,
    "browser_snapshot": tool_browser_snapshot,
    "browser_eval": tool_browser_eval,
    "browser_get_dom": tool_browser_get_dom,
}


def main():
    payload = _load_payload()
    tool = payload.get("tool", "browser_navigate")
    handler = TOOLS.get(tool)
    if not handler:
        _write_output({"error": f"Tool desconocido: {tool}"})
        return
    result = handler(payload)
    _write_output(result)


if __name__ == "__main__":
    main()
