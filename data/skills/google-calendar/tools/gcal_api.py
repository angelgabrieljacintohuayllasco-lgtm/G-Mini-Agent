from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
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
    """Obtiene access_token usando Google Service Account JSON o API Key."""
    creds_json = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "").strip()
    if not creds_json:
        raise ValueError("Falta GOOGLE_CALENDAR_CREDENTIALS_JSON")

    # Si es un API key simple, usarlo directamente
    if not creds_json.startswith("{"):
        return creds_json

    # Service Account JSON → generar JWT y exchangear por access_token
    import time
    import hashlib
    import hmac
    import base64

    creds = json.loads(creds_json)
    sa_email = creds.get("client_email", "")
    private_key = creds.get("private_key", "")

    if not sa_email or not private_key:
        raise ValueError("Credenciales de service account incompletas")

    # Para service accounts, usar google-auth si está disponible
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        credentials.refresh(Request())
        return credentials.token
    except ImportError:
        raise ImportError(
            "Instala google-auth: pip install google-auth google-auth-httplib2"
        )


def _api_call(endpoint: str, method: str = "GET", data: dict = None, token: str = "") -> dict:
    url = f"https://www.googleapis.com/calendar/v3/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {err}")


def handle_list_events(params: dict, token: str) -> dict:
    cal_id = params.get("calendar_id", "primary")
    max_results = min(params.get("max_results", 10), 50)
    time_min = params.get("time_min", datetime.now(timezone.utc).isoformat())
    time_max = params.get("time_max", "")

    qs = f"calendars/{cal_id}/events?maxResults={max_results}&singleEvents=true&orderBy=startTime&timeMin={time_min}"
    if time_max:
        qs += f"&timeMax={time_max}"

    data = _api_call(qs, token=token)
    events = []
    for item in data.get("items", []):
        events.append({
            "id": item.get("id"),
            "summary": item.get("summary", ""),
            "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
            "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
            "location": item.get("location", ""),
            "description": item.get("description", "")[:200],
        })
    return {"status": "success", "events": events, "count": len(events)}


def handle_create_event(params: dict, token: str) -> dict:
    cal_id = params.get("calendar_id", "primary")
    body = {
        "summary": params.get("summary", "Evento sin título"),
        "start": {"dateTime": params["start"], "timeZone": params.get("timezone", "America/Mexico_City")},
        "end": {"dateTime": params["end"], "timeZone": params.get("timezone", "America/Mexico_City")},
    }
    if params.get("description"):
        body["description"] = params["description"]
    if params.get("location"):
        body["location"] = params["location"]

    result = _api_call(f"calendars/{cal_id}/events", method="POST", data=body, token=token)
    return {"status": "success", "event_id": result.get("id"), "link": result.get("htmlLink")}


def handle_update_event(params: dict, token: str) -> dict:
    cal_id = params.get("calendar_id", "primary")
    event_id = params.get("event_id")
    if not event_id:
        return {"status": "error", "message": "Falta event_id"}

    body = {}
    if "summary" in params:
        body["summary"] = params["summary"]
    if "description" in params:
        body["description"] = params["description"]
    if "start" in params:
        body["start"] = {"dateTime": params["start"], "timeZone": params.get("timezone", "America/Mexico_City")}
    if "end" in params:
        body["end"] = {"dateTime": params["end"], "timeZone": params.get("timezone", "America/Mexico_City")}

    result = _api_call(f"calendars/{cal_id}/events/{event_id}", method="PATCH", data=body, token=token)
    return {"status": "success", "event_id": result.get("id")}


def handle_delete_event(params: dict, token: str) -> dict:
    cal_id = params.get("calendar_id", "primary")
    event_id = params.get("event_id")
    if not event_id:
        return {"status": "error", "message": "Falta event_id"}

    _api_call(f"calendars/{cal_id}/events/{event_id}", method="DELETE", token=token)
    return {"status": "success", "deleted": event_id}


def handle_freebusy(params: dict, token: str) -> dict:
    cal_id = params.get("calendar_id", "primary")
    body = {
        "timeMin": params["time_min"],
        "timeMax": params["time_max"],
        "items": [{"id": cal_id}],
    }
    result = _api_call("freeBusy", method="POST", data=body, token=token)
    busy = result.get("calendars", {}).get(cal_id, {}).get("busy", [])
    return {"status": "success", "busy_periods": busy}


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
        "gcal_list_events": handle_list_events,
        "gcal_create_event": handle_create_event,
        "gcal_update_event": handle_update_event,
        "gcal_delete_event": handle_delete_event,
        "gcal_freebusy": handle_freebusy,
    }

    handler = handlers.get(tool_name)
    if not handler:
        _write_output({"error": f"Herramienta no reconocida: {tool_name}"})
        return 1

    try:
        result = handler(user_input, token)
        _write_output(result)
        return 0 if result.get("status") == "success" else 1
    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
