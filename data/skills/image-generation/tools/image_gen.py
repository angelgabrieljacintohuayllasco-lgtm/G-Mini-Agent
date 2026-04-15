from __future__ import annotations
import json
import os
import base64
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


def _openai_call(endpoint: str, data: dict, api_key: str) -> dict:
    url = f"https://api.openai.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {err}")


def _save_b64_image(b64_data: str, output_path: str) -> str:
    img_bytes = base64.b64decode(b64_data)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(img_bytes)
    return str(path.resolve())


def _download_url(url: str, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        path.write_bytes(resp.read())
    return str(path.resolve())


def handle_generate(params: dict, api_key: str) -> dict:
    prompt = params.get("prompt", "")
    if not prompt:
        return {"status": "error", "message": "Falta el prompt"}

    size = params.get("size", "1024x1024")
    quality = params.get("quality", "standard")
    output_path = params.get("output_path", "")

    data = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "response_format": "b64_json" if output_path else "url",
    }

    result = _openai_call("images/generations", data, api_key)
    image_data = result.get("data", [{}])[0]

    if output_path and image_data.get("b64_json"):
        saved = _save_b64_image(image_data["b64_json"], output_path)
        return {"status": "success", "saved_path": saved, "revised_prompt": image_data.get("revised_prompt", "")}
    elif image_data.get("url"):
        url = image_data["url"]
        if output_path:
            saved = _download_url(url, output_path)
            return {"status": "success", "saved_path": saved, "revised_prompt": image_data.get("revised_prompt", "")}
        return {"status": "success", "url": url, "revised_prompt": image_data.get("revised_prompt", "")}

    return {"status": "error", "message": "No se recibió imagen"}


def handle_edit(params: dict, api_key: str) -> dict:
    prompt = params.get("prompt", "")
    image_path = params.get("image_path", "")
    if not prompt or not image_path:
        return {"status": "error", "message": "Faltan prompt e image_path"}

    output_path = params.get("output_path", "")

    # Para ediciones, necesitamos multipart upload
    import io
    import http.client
    import uuid

    boundary = uuid.uuid4().hex
    lines = []

    # Prompt field
    lines.append(f"--{boundary}")
    lines.append('Content-Disposition: form-data; name="prompt"')
    lines.append("")
    lines.append(prompt)

    # Model
    lines.append(f"--{boundary}")
    lines.append('Content-Disposition: form-data; name="model"')
    lines.append("")
    lines.append("dall-e-2")

    # Response format
    lines.append(f"--{boundary}")
    lines.append('Content-Disposition: form-data; name="response_format"')
    lines.append("")
    lines.append("b64_json" if output_path else "url")

    # Image file
    img_data = Path(image_path).read_bytes()
    lines.append(f"--{boundary}")
    lines.append(f'Content-Disposition: form-data; name="image"; filename="image.png"')
    lines.append("Content-Type: image/png")
    lines.append("")

    body_start = "\r\n".join(lines).encode("utf-8") + b"\r\n"
    body_end = f"\r\n--{boundary}--\r\n".encode("utf-8")

    # Mask (optional)
    mask_part = b""
    mask_path = params.get("mask_path", "")
    if mask_path and Path(mask_path).exists():
        mask_data = Path(mask_path).read_bytes()
        mask_lines = [
            f"--{boundary}",
            f'Content-Disposition: form-data; name="mask"; filename="mask.png"',
            "Content-Type: image/png",
            "",
        ]
        mask_part = b"\r\n" + "\r\n".join(mask_lines).encode("utf-8") + b"\r\n" + mask_data

    full_body = body_start + img_data + mask_part + body_end

    conn = http.client.HTTPSConnection("api.openai.com", timeout=90)
    conn.request(
        "POST",
        "/v1/images/edits",
        body=full_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    resp = conn.getresponse()
    resp_body = resp.read().decode("utf-8")
    if resp.status != 200:
        return {"status": "error", "message": f"HTTP {resp.status}: {resp_body}"}

    result = json.loads(resp_body)
    image_item = result.get("data", [{}])[0]

    if output_path and image_item.get("b64_json"):
        saved = _save_b64_image(image_item["b64_json"], output_path)
        return {"status": "success", "saved_path": saved}
    elif image_item.get("url"):
        if output_path:
            saved = _download_url(image_item["url"], output_path)
            return {"status": "success", "saved_path": saved}
        return {"status": "success", "url": image_item["url"]}

    return {"status": "error", "message": "No se recibió imagen editada"}


def handle_variations(params: dict, api_key: str) -> dict:
    image_path = params.get("image_path", "")
    if not image_path:
        return {"status": "error", "message": "Falta image_path"}

    n = min(params.get("n", 1), 4)
    output_dir = params.get("output_dir", "")

    data = {
        "model": "dall-e-2",
        "n": n,
        "response_format": "url",
    }

    # Variaciones también necesitan multipart
    import uuid
    import http.client

    boundary = uuid.uuid4().hex
    lines = [
        f"--{boundary}",
        'Content-Disposition: form-data; name="model"',
        "",
        "dall-e-2",
        f"--{boundary}",
        'Content-Disposition: form-data; name="n"',
        "",
        str(n),
        f"--{boundary}",
        'Content-Disposition: form-data; name="response_format"',
        "",
        "b64_json" if output_dir else "url",
        f"--{boundary}",
        f'Content-Disposition: form-data; name="image"; filename="image.png"',
        "Content-Type: image/png",
        "",
    ]

    img_data = Path(image_path).read_bytes()
    body = "\r\n".join(lines).encode("utf-8") + b"\r\n" + img_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    conn = http.client.HTTPSConnection("api.openai.com", timeout=90)
    conn.request(
        "POST",
        "/v1/images/variations",
        body=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    resp = conn.getresponse()
    resp_body = resp.read().decode("utf-8")
    if resp.status != 200:
        return {"status": "error", "message": f"HTTP {resp.status}: {resp_body}"}

    result = json.loads(resp_body)
    images = result.get("data", [])
    saved_paths = []

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        for i, img in enumerate(images):
            if img.get("b64_json"):
                p = str(Path(output_dir) / f"variation_{i+1}.png")
                _save_b64_image(img["b64_json"], p)
                saved_paths.append(p)
            elif img.get("url"):
                p = str(Path(output_dir) / f"variation_{i+1}.png")
                _download_url(img["url"], p)
                saved_paths.append(p)
        return {"status": "success", "saved_paths": saved_paths}

    urls = [img.get("url", "") for img in images]
    return {"status": "success", "urls": urls}


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        _write_output({"error": "Falta OPENAI_API_KEY"})
        return 1

    handlers = {
        "dalle_generate": handle_generate,
        "dalle_edit": handle_edit,
        "dalle_variations": handle_variations,
    }

    handler = handlers.get(tool_name)
    if not handler:
        _write_output({"error": f"Herramienta no reconocida: {tool_name}"})
        return 1

    try:
        result = handler(user_input, api_key)
        _write_output(result)
        return 0 if result.get("status") == "success" else 1
    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
