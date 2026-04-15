"""
ide-control skill — Control de VS Code / Cursor via backend API.
Wrapper de las acciones ide_* del planner de G-Mini Agent.
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
    url = f"{BACKEND_URL}/actions/execute"
    body = json.dumps({
        "actions": [{"type": action_type, "params": params}],
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def tool_ide_open_file(payload: dict[str, Any]) -> dict[str, Any]:
    path = payload.get("path", "").strip()
    if not path:
        return {"error": "Se requiere 'path'"}
    params: dict[str, Any] = {"path": path}
    if payload.get("line"):
        params["line"] = int(payload["line"])
    return _backend_action("ide_open_file", params)


def tool_ide_apply_edit(payload: dict[str, Any]) -> dict[str, Any]:
    path = payload.get("path", "").strip()
    edit = payload.get("edit", "").strip()
    if not path or not edit:
        return {"error": "Se requiere 'path' y 'edit'"}
    return _backend_action("ide_apply_edit", {"path": path, "edit": edit})


def tool_ide_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if payload.get("path"):
        params["path"] = payload["path"]
    return _backend_action("ide_diagnostics", params)


def tool_ide_symbols(payload: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if payload.get("path"):
        params["path"] = payload["path"]
    if payload.get("query"):
        params["query"] = payload["query"]
    return _backend_action("ide_symbols", params)


def tool_ide_state(payload: dict[str, Any]) -> dict[str, Any]:
    return _backend_action("ide_state", {})


def tool_ide_open_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    path = payload.get("path", "").strip()
    if not path:
        return {"error": "Se requiere 'path'"}
    return _backend_action("ide_open_workspace", {"path": path})


TOOLS = {
    "ide_open_file": tool_ide_open_file,
    "ide_apply_edit": tool_ide_apply_edit,
    "ide_diagnostics": tool_ide_diagnostics,
    "ide_symbols": tool_ide_symbols,
    "ide_state": tool_ide_state,
    "ide_open_workspace": tool_ide_open_workspace,
}


def main():
    payload = _load_payload()
    tool = payload.get("tool", "ide_state")
    handler = TOOLS.get(tool)
    if not handler:
        _write_output({"error": f"Tool desconocido: {tool}"})
        return
    result = handler(payload)
    _write_output(result)


if __name__ == "__main__":
    main()
