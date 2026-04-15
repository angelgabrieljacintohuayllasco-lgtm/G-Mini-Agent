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


def _get_access_token() -> str:
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "").strip()
    if not creds_json:
        raise ValueError("Falta GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json.startswith("{"):
        return creds_json

    creds = json.loads(creds_json)
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        credentials.refresh(Request())
        return credentials.token
    except ImportError:
        raise ImportError("Instala google-auth: pip install google-auth")


def _api_call(endpoint: str, method: str = "GET", data: dict = None, token: str = "") -> dict:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {err}")


def handle_read(params: dict, token: str) -> dict:
    sid = params["spreadsheet_id"]
    rng = params.get("range", "Sheet1")
    render = params.get("value_render", "FORMATTED_VALUE")
    encoded_range = urllib.request.quote(rng, safe="")
    data = _api_call(f"{sid}/values/{encoded_range}?valueRenderOption={render}", token=token)
    return {"status": "success", "values": data.get("values", []), "range": data.get("range", "")}


def handle_write(params: dict, token: str) -> dict:
    sid = params["spreadsheet_id"]
    rng = params.get("range", "Sheet1")
    values = params.get("values", [])
    input_option = params.get("input_option", "USER_ENTERED")
    encoded_range = urllib.request.quote(rng, safe="")
    body = {"values": values}
    result = _api_call(
        f"{sid}/values/{encoded_range}?valueInputOption={input_option}",
        method="PUT", data=body, token=token,
    )
    return {
        "status": "success",
        "updated_cells": result.get("updatedCells", 0),
        "updated_range": result.get("updatedRange", ""),
    }


def handle_append(params: dict, token: str) -> dict:
    sid = params["spreadsheet_id"]
    rng = params.get("range", "Sheet1")
    values = params.get("values", [])
    encoded_range = urllib.request.quote(rng, safe="")
    body = {"values": values}
    result = _api_call(
        f"{sid}/values/{encoded_range}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS",
        method="POST", data=body, token=token,
    )
    updates = result.get("updates", {})
    return {
        "status": "success",
        "updated_cells": updates.get("updatedCells", 0),
        "updated_range": updates.get("updatedRange", ""),
    }


def handle_create(params: dict, token: str) -> dict:
    title = params.get("title", "Nuevo Spreadsheet")
    body = {"properties": {"title": title}}
    result = _api_call("", method="POST", data=body, token=token)
    return {
        "status": "success",
        "spreadsheet_id": result.get("spreadsheetId"),
        "url": result.get("spreadsheetUrl"),
    }


def handle_info(params: dict, token: str) -> dict:
    sid = params["spreadsheet_id"]
    data = _api_call(sid, token=token)
    props = data.get("properties", {})
    sheets = [
        {"title": s.get("properties", {}).get("title"), "index": s.get("properties", {}).get("index")}
        for s in data.get("sheets", [])
    ]
    return {"status": "success", "title": props.get("title"), "locale": props.get("locale"), "sheets": sheets}


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")

    try:
        token = _get_access_token()
    except Exception as e:
        _write_output({"error": str(e)})
        return 1

    handlers = {
        "gsheets_read": handle_read,
        "gsheets_write": handle_write,
        "gsheets_append": handle_append,
        "gsheets_create": handle_create,
        "gsheets_info": handle_info,
    }

    handler = handlers.get(tool_name)
    if not handler:
        _write_output({"error": f"Herramienta no reconocida: {tool_name}"})
        return 1

    try:
        result = handler(user_input, token)
        _write_output(result)
        return 0
    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
