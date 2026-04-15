from __future__ import annotations
import json
import os
import subprocess
import shutil
import tempfile
from pathlib import Path


def _load_payload() -> dict:
    input_path = os.getenv("GMINI_SKILL_INPUT", "").strip()
    if input_path and Path(input_path).exists():
        return json.loads(Path(input_path).read_text(encoding="utf-8"))
    try:
        raw = input()
    except EOFError:
        return {}
    raw = raw.strip()
    return json.loads(raw) if raw else {}


def _write_output(result: dict) -> None:
    output_path = os.getenv("GMINI_SKILL_OUTPUT", "").strip()
    if output_path:
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False))


def _find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FileNotFoundError("ffmpeg no encontrado en PATH. Instálalo primero.")
    return path


def _run(args: list[str], timeout: int = 300) -> dict:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:] if result.stdout else "",
        "stderr": result.stderr[-4000:] if result.stderr else "",
    }


def _validate_path(p: str) -> str:
    """Valida que la ruta no intente escapes de directorio peligrosos."""
    resolved = str(Path(p).resolve())
    return resolved


def handle_convert(params: dict) -> dict:
    ffmpeg = _find_ffmpeg()
    inp = _validate_path(params["input_path"])
    out = _validate_path(params["output_path"])
    extra = params.get("extra_args", [])
    if not isinstance(extra, list):
        extra = []

    cmd = [ffmpeg, "-y", "-i", inp] + extra + [out]
    r = _run(cmd)
    if r["returncode"] != 0:
        return {"status": "error", "message": r["stderr"]}
    return {"status": "success", "output_path": out}


def handle_cut(params: dict) -> dict:
    ffmpeg = _find_ffmpeg()
    inp = _validate_path(params["input_path"])
    out = _validate_path(params["output_path"])
    start = params.get("start", "00:00:00")
    duration = params.get("duration", "00:00:30")

    cmd = [ffmpeg, "-y", "-i", inp, "-ss", start, "-t", duration, "-c", "copy", out]
    r = _run(cmd)
    if r["returncode"] != 0:
        return {"status": "error", "message": r["stderr"]}
    return {"status": "success", "output_path": out}


def handle_merge(params: dict) -> dict:
    ffmpeg = _find_ffmpeg()
    inputs = params.get("input_paths", [])
    out = _validate_path(params["output_path"])

    if len(inputs) < 2:
        return {"status": "error", "message": "Se necesitan al menos 2 archivos para unir."}

    # Crear archivo de lista temporal
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in inputs:
            vp = _validate_path(p)
            f.write(f"file '{vp}'\n")
        list_file = f.name

    try:
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out]
        r = _run(cmd, timeout=600)
        if r["returncode"] != 0:
            return {"status": "error", "message": r["stderr"]}
        return {"status": "success", "output_path": out}
    finally:
        os.unlink(list_file)


def handle_extract_audio(params: dict) -> dict:
    ffmpeg = _find_ffmpeg()
    inp = _validate_path(params["input_path"])
    fmt = params.get("format", "mp3")
    out = _validate_path(params.get("output_path", inp.rsplit(".", 1)[0] + f".{fmt}"))

    cmd = [ffmpeg, "-y", "-i", inp, "-vn", "-acodec", "libmp3lame" if fmt == "mp3" else "copy", out]
    r = _run(cmd)
    if r["returncode"] != 0:
        return {"status": "error", "message": r["stderr"]}
    return {"status": "success", "output_path": out}


def handle_info(params: dict) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"status": "error", "message": "ffprobe no encontrado en PATH."}
    inp = _validate_path(params["input_path"])

    cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", inp]
    r = _run(cmd, timeout=30)
    if r["returncode"] != 0:
        return {"status": "error", "message": r["stderr"]}
    try:
        info = json.loads(r["stdout"])
    except json.JSONDecodeError:
        info = {"raw": r["stdout"]}
    return {"status": "success", "info": info}


def handle_thumbnail(params: dict) -> dict:
    ffmpeg = _find_ffmpeg()
    inp = _validate_path(params["input_path"])
    out = _validate_path(params["output_path"])
    time = params.get("time", "00:00:05")

    cmd = [ffmpeg, "-y", "-i", inp, "-ss", time, "-vframes", "1", out]
    r = _run(cmd, timeout=60)
    if r["returncode"] != 0:
        return {"status": "error", "message": r["stderr"]}
    return {"status": "success", "output_path": out}


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")

    handlers = {
        "ffmpeg_convert": handle_convert,
        "ffmpeg_cut": handle_cut,
        "ffmpeg_merge": handle_merge,
        "ffmpeg_extract_audio": handle_extract_audio,
        "ffmpeg_info": handle_info,
        "ffmpeg_thumbnail": handle_thumbnail,
    }

    handler = handlers.get(tool_name)
    if not handler:
        _write_output({"error": f"Herramienta no reconocida: {tool_name}"})
        return 1

    try:
        result = handler(user_input)
        _write_output(result)
        return 0 if result.get("status") == "success" else 1
    except FileNotFoundError as e:
        _write_output({"error": str(e)})
        return 1
    except Exception as e:
        _write_output({"error": f"Error inesperado: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
