from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
import hmac
import hashlib
import time
import base64
import uuid
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


def _percent_encode(s: str) -> str:
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return "".join(c if c in safe else f"%{ord(c):02X}" for c in str(s))


def _oauth1_header(method: str, url: str, params: dict) -> str:
    """Genera OAuth 1.0a header para Twitter API v2."""
    api_key = os.getenv("TWITTER_API_KEY", "")
    api_secret = os.getenv("TWITTER_API_SECRET", "")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        raise ValueError("Faltan credenciales OAuth de Twitter")

    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    # Combinar todos los parámetros para la firma
    all_params = {**params, **oauth_params}
    param_str = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in sorted(all_params.items())
    )
    base_str = f"{method.upper()}&{_percent_encode(url)}&{_percent_encode(param_str)}"
    signing_key = f"{_percent_encode(api_secret)}&{_percent_encode(access_secret)}"

    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = sig

    header = ", ".join(f'{k}="{_percent_encode(v)}"' for k, v in sorted(oauth_params.items()))
    return f"OAuth {header}"


def handle_post(params: dict) -> dict:
    text = params.get("text", "")
    if not text:
        return {"status": "error", "message": "Falta el texto del tweet"}
    if len(text) > 280:
        return {"status": "error", "message": f"Tweet excede 280 caracteres ({len(text)})"}

    url = "https://api.twitter.com/2/tweets"
    body = {"text": text}
    if params.get("reply_to"):
        body["reply"] = {"in_reply_to_tweet_id": params["reply_to"]}

    auth = _oauth1_header("POST", url, {})
    body_bytes = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=body_bytes, headers={
        "Authorization": auth,
        "Content-Type": "application/json",
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            tweet_id = result.get("data", {}).get("id", "")
            return {"status": "success", "tweet_id": tweet_id, "url": f"https://twitter.com/i/status/{tweet_id}"}
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode()}"}


def handle_search(params: dict) -> dict:
    query = params.get("query", "")
    if not query:
        return {"status": "error", "message": "Falta el query de búsqueda"}

    bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
    if not bearer:
        return {"status": "error", "message": "Falta TWITTER_BEARER_TOKEN"}

    max_results = min(max(params.get("max_results", 10), 10), 100)
    encoded_q = urllib.request.quote(query)
    url = f"https://api.twitter.com/2/tweets/search/recent?query={encoded_q}&max_results={max_results}&tweet.fields=created_at,author_id,public_metrics"

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode()}"}

    tweets = []
    for t in data.get("data", []):
        tweets.append({
            "id": t.get("id"),
            "text": t.get("text"),
            "author_id": t.get("author_id"),
            "created_at": t.get("created_at"),
            "metrics": t.get("public_metrics", {}),
        })
    return {"status": "success", "tweets": tweets, "count": len(tweets)}


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")

    handlers = {
        "twitter_post": handle_post,
        "twitter_search": handle_search,
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
