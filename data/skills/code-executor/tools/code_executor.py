"""
code-executor skill — Ejecución de código Python y shell en sandbox.
Tools: execute_python, execute_shell
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any

MAX_OUTPUT = 50_000  # chars


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


def tool_execute_python(payload: dict[str, Any]) -> dict[str, Any]:
    code = payload.get("code", "").strip()
    if not code:
        return {"error": "Se requiere 'code'"}

    timeout = min(int(payload.get("timeout", 30)), 120)
    working_dir = payload.get("working_dir") or tempfile.gettempdir()

    # Write code to temp file
    fd, tmp_path = tempfile.mkstemp(suffix=".py", prefix="gmini_exec_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        env = os.environ.copy()
        # Remove sensitive keys
        for key in list(env.keys()):
            if any(s in key.upper() for s in ("SECRET", "TOKEN", "PASSWORD", "KEY")):
                if key not in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "HOME"):
                    del env[key]

        result = subprocess.run(
            [sys.executable, "-u", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            env=env,
        )

        return {
            "stdout": result.stdout[:MAX_OUTPUT] if result.stdout else "",
            "stderr": result.stderr[:MAX_OUTPUT] if result.stderr else "",
            "exit_code": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout después de {timeout}s", "exit_code": -1, "success": False}
    except Exception as e:
        return {"error": str(e), "exit_code": -1, "success": False}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def tool_execute_shell(payload: dict[str, Any]) -> dict[str, Any]:
    command = payload.get("command", "").strip()
    if not command:
        return {"error": "Se requiere 'command'"}

    # Block dangerous patterns
    blocked = ["rm -rf /", "format c:", "del /f /s /q c:", ":(){ :|:&", "mkfs", "> /dev/sda"]
    cmd_lower = command.lower()
    for pattern in blocked:
        if pattern in cmd_lower:
            return {"error": f"Comando bloqueado por seguridad: '{pattern}'"}

    timeout = min(int(payload.get("timeout", 30)), 120)
    working_dir = payload.get("working_dir") or tempfile.gettempdir()

    try:
        is_windows = sys.platform == "win32"
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            shell=False if not is_windows else True,
        )

        return {
            "stdout": result.stdout[:MAX_OUTPUT] if result.stdout else "",
            "stderr": result.stderr[:MAX_OUTPUT] if result.stderr else "",
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout después de {timeout}s", "exit_code": -1, "success": False}
    except Exception as e:
        return {"error": str(e), "exit_code": -1, "success": False}


def main():
    payload = _load_payload()
    tool = payload.get("tool", "execute_python")
    if tool == "execute_shell":
        result = tool_execute_shell(payload)
    else:
        result = tool_execute_python(payload)
    _write_output(result)


if __name__ == "__main__":
    main()
