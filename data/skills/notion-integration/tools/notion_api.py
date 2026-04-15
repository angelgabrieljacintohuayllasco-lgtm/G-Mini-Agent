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

def api_call(endpoint: str, method: str, data: dict = None, token: str = "") -> dict:
    url = f"https://api.notion.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read()
            return json.loads(res_body.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {err_body}")
    except Exception as e:
        raise Exception(str(e))

def handle_query_database(user_input: dict, token: str):
    db_id = user_input.get("database_id")
    if not db_id:
        return {"error": "Falta 'database_id'."}
    
    payload = {}
    if "filter" in user_input and user_input["filter"]:
        payload["filter"] = user_input["filter"]
        
    res = api_call(f"databases/{db_id}/query", "POST", payload, token)
    return {"status": "success", "results": res.get("results", [])}

def handle_create_page(user_input: dict, token: str):
    parent_id = user_input.get("parent_id")
    is_db = user_input.get("is_database", True)
    title = user_input.get("title", "Sin título")
    props = user_input.get("properties", {})
    
    if not parent_id:
        return {"error": "Falta 'parent_id'."}
    
    payload = {
        "parent": {
            "database_id" if is_db else "page_id": parent_id
        },
        "properties": props
    }
    
    # Si properties viene vacío y es una DB, agregamos al menos el título
    if is_db and not props:
        payload["properties"] = {
            "title": [
                {
                    "text": {"content": title}
                }
            ]
        }
        
    res = api_call("pages", "POST", payload, token)
    return {"status": "success", "page_id": res.get("id"), "url": res.get("url")}

def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    tool_name = payload.get("tool", "")
    
    token = os.getenv("NOTION_API_KEY")
    if not token:
        _write_output({"error": "Falta variable de entorno NOTION_API_KEY."})
        return 1
        
    try:
        if tool_name == "notion_query_database":
            res = handle_query_database(user_input, token)
        elif tool_name == "notion_create_page":
            res = handle_create_page(user_input, token)
        else:
            # Fallback a inferir del propio nombre de herramienta en el input
            if "database_id" in user_input:
                res = handle_query_database(user_input, token)
            elif "parent_id" in user_input:
                res = handle_create_page(user_input, token)
            else:
                res = {"error": "Acción no reconocida."}
                
        _write_output(res)
        return 0 if "error" not in res else 1
    except Exception as e:
        _write_output({"error": str(e)})
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
