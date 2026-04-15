"""
web-search skill — Búsqueda web con Tavily API o SearXNG.
Tools: web_search, web_extract
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.parse
from typing import Any


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


def _tavily_search(query: str, api_key: str, max_results: int = 5, search_depth: str = "basic") -> dict[str, Any]:
    url = "https://api.tavily.com/search"
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": True,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _tavily_extract(url_target: str, api_key: str) -> dict[str, Any]:
    url = "https://api.tavily.com/extract"
    payload = json.dumps({
        "api_key": api_key,
        "urls": [url_target],
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _searxng_search(query: str, base_url: str, max_results: int = 5) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "pageno": 1,
    })
    url = f"{base_url}/search?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    results = []
    for r in (data.get("results") or [])[:max_results]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        })
    return {"results": results, "answer": data.get("infoboxes", [{}])[0].get("content", "") if data.get("infoboxes") else ""}


def tool_web_search(payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("query", "").strip()
    if not query:
        return {"error": "Se requiere 'query'"}

    max_results = int(payload.get("max_results", 5))
    search_depth = payload.get("search_depth", "basic")

    api_key = payload.get("api_key") or os.environ.get("TAVILY_API_KEY", "")
    searxng_url = payload.get("searxng_url") or os.environ.get("SEARXNG_URL", "")

    if api_key:
        try:
            data = _tavily_search(query, api_key, max_results, search_depth)
            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0),
                })
            return {
                "provider": "tavily",
                "query": query,
                "answer": data.get("answer", ""),
                "results": results,
                "total": len(results),
            }
        except Exception as e:
            return {"error": f"Tavily error: {e}"}

    elif searxng_url:
        try:
            data = _searxng_search(query, searxng_url.rstrip("/"), max_results)
            return {
                "provider": "searxng",
                "query": query,
                "answer": data.get("answer", ""),
                "results": data.get("results", []),
                "total": len(data.get("results", [])),
            }
        except Exception as e:
            return {"error": f"SearXNG error: {e}"}

    return {"error": "Se requiere TAVILY_API_KEY o SEARXNG_URL"}


def tool_web_extract(payload: dict[str, Any]) -> dict[str, Any]:
    url_target = payload.get("url", "").strip()
    if not url_target:
        return {"error": "Se requiere 'url'"}

    api_key = payload.get("api_key") or os.environ.get("TAVILY_API_KEY", "")
    if api_key:
        try:
            data = _tavily_extract(url_target, api_key)
            results = data.get("results", [])
            if results:
                return {
                    "url": url_target,
                    "content": results[0].get("raw_content", ""),
                    "provider": "tavily",
                }
            return {"url": url_target, "content": "", "error": "Sin contenido"}
        except Exception as e:
            return {"error": f"Tavily extract error: {e}"}

    # Fallback: direct fetch
    try:
        req = urllib.request.Request(url_target, headers={
            "User-Agent": "Mozilla/5.0 (G-Mini Agent)"
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        # Basic HTML stripping
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return {
            "url": url_target,
            "content": text[:12000],
            "provider": "direct",
        }
    except Exception as e:
        return {"error": f"Fetch error: {e}"}


def main():
    payload = _load_payload()
    tool = payload.get("tool", "web_search")
    if tool == "web_extract":
        result = tool_web_extract(payload)
    else:
        result = tool_web_search(payload)
    _write_output(result)


if __name__ == "__main__":
    main()
