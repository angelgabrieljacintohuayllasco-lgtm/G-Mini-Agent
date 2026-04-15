from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
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


def handle_post(params: dict) -> dict:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        return {"status": "error", "message": "Falta LINKEDIN_ACCESS_TOKEN"}

    text = params.get("text", "")
    if not text:
        return {"status": "error", "message": "Falta el texto de la publicación"}

    visibility = params.get("visibility", "PUBLIC")

    # Primero obtener el URN del usuario
    me_url = "https://api.linkedin.com/v2/userinfo"
    req = urllib.request.Request(me_url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            me = json.loads(resp.read().decode("utf-8"))
            person_urn = f"urn:li:person:{me.get('sub', '')}"
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"Error obteniendo perfil: HTTP {e.code}"}

    # Publicar
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
    }

    body_bytes = json.dumps(body).encode("utf-8")
    req2 = urllib.request.Request(post_url, data=body_bytes, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }, method="POST")

    try:
        with urllib.request.urlopen(req2, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"status": "success", "post_id": result.get("id", "")}
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode()}"}


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")

    if tool_name == "linkedin_post":
        result = handle_post(user_input)
    else:
        result = {"error": f"Herramienta no reconocida: {tool_name}"}

    _write_output(result)
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
