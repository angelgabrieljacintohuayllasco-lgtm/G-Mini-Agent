from __future__ import annotations

import json
import os
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
    if not raw:
        return {}
    return json.loads(raw)


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input") if isinstance(payload.get("input"), dict) else {}

    raw_path = str(user_input.get("path", "")).strip()
    inline_text = str(user_input.get("text", ""))
    max_preview_chars = user_input.get("max_preview_chars", 240)
    try:
        max_preview_chars = max(40, min(int(max_preview_chars), 2000))
    except (TypeError, ValueError):
        max_preview_chars = 240

    result: dict[str, object]
    if raw_path:
        path = Path(raw_path).expanduser()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"No existe el archivo de texto: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        result = {
            "source": "path",
            "path": str(path.resolve()),
            "exists": True,
        }
    else:
        text = inline_text
        result = {
            "source": "inline",
            "path": None,
            "exists": False,
        }

    normalized = text.replace("\r\n", "\n")
    result.update(
        {
            "chars": len(text),
            "words": len([chunk for chunk in normalized.split() if chunk]),
            "lines": len(normalized.splitlines()) or (1 if normalized else 0),
            "preview": normalized[:max_preview_chars],
        }
    )

    output_path = os.getenv("GMINI_SKILL_OUTPUT", "").strip()
    if output_path:
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
