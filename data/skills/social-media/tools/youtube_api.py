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


def _get_youtube_token() -> str:
    creds_json = os.getenv("GOOGLE_YOUTUBE_CREDENTIALS_JSON", "").strip()
    if not creds_json:
        raise ValueError("Falta GOOGLE_YOUTUBE_CREDENTIALS_JSON")
    if not creds_json.startswith("{"):
        return creds_json
    creds = json.loads(creds_json)
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=["https://www.googleapis.com/auth/youtube"]
        )
        credentials.refresh(Request())
        return credentials.token
    except ImportError:
        raise ImportError("Instala google-auth: pip install google-auth")


def handle_upload(params: dict) -> dict:
    token = _get_youtube_token()
    video_path = params.get("video_path", "")
    title = params.get("title", "Video sin título")
    description = params.get("description", "")
    tags = params.get("tags", [])
    privacy = params.get("privacy", "private")

    if not video_path or not Path(video_path).exists():
        return {"status": "error", "message": f"Video no encontrado: {video_path}"}

    # Metadata
    metadata = {
        "snippet": {"title": title, "description": description, "tags": tags, "categoryId": "22"},
        "status": {"privacyStatus": privacy},
    }

    # Resumable upload init
    meta_bytes = json.dumps(metadata).encode("utf-8")
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    req = urllib.request.Request(init_url, data=meta_bytes, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*",
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            upload_url = resp.headers.get("Location")
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"Init upload: HTTP {e.code}: {e.read().decode()}"}

    if not upload_url:
        return {"status": "error", "message": "No se recibió URL de upload"}

    # Upload video
    video_bytes = Path(video_path).read_bytes()
    req2 = urllib.request.Request(upload_url, data=video_bytes, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "video/*",
        "Content-Length": str(len(video_bytes)),
    }, method="PUT")

    try:
        with urllib.request.urlopen(req2, timeout=600) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "success",
                "video_id": result.get("id"),
                "url": f"https://youtu.be/{result.get('id')}",
            }
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"Upload: HTTP {e.code}: {e.read().decode()}"}


def handle_list_videos(params: dict) -> dict:
    token = _get_youtube_token()
    max_results = min(params.get("max_results", 10), 50)

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&forMine=true&type=video&maxResults={max_results}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode()}"}

    videos = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        vid = item.get("id", {}).get("videoId", "")
        videos.append({
            "id": vid,
            "title": snippet.get("title"),
            "published_at": snippet.get("publishedAt"),
            "url": f"https://youtu.be/{vid}",
        })
    return {"status": "success", "videos": videos}


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")

    handlers = {
        "youtube_upload": handle_upload,
        "youtube_list_videos": handle_list_videos,
    }

    handler = handlers.get(tool_name)
    if not handler:
        _write_output({"error": f"Herramienta no reconocida: {tool_name}"})
        return 1

    try:
        result = handler(user_input)
        _write_output(result)
        return 0 if result.get("status") == "success" else 1
    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
