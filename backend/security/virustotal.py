"""
VirusTotal scanning helpers for downloaded files.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from backend.config import config


class VirusTotalScanner:
    """Scans files with VirusTotal before they are considered safe to use."""

    BASE_URL = "https://www.virustotal.com/api/v3"
    DEFAULT_POLL_INTERVAL = 5
    DEFAULT_TIMEOUT_SECONDS = 120

    def __init__(self) -> None:
        self._api_key = config.get_api_key("virustotal_api") or ""

    def refresh_api_key(self) -> None:
        self._api_key = config.get_api_key("virustotal_api") or ""

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def scan_file(
        self,
        file_path: str | Path,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {
                "configured": self.is_configured(),
                "status": "missing_file",
                "trusted": False,
                "file_path": str(path),
            }

        if not self.is_configured():
            return {
                "configured": False,
                "status": "api_key_missing",
                "trusted": False,
                "file_path": str(path),
            }

        file_hash = self._sha256(path)
        headers = {"x-apikey": self._api_key}

        async with aiohttp.ClientSession(headers=headers) as session:
            existing = await self._get_existing_report(session, file_hash)
            if existing is not None:
                verdict = self._verdict_from_report(existing, str(path), file_hash)
                verdict["source"] = "existing_report"
                return verdict

            analysis_id = await self._upload_file(session, path)
            report = await self._poll_analysis(session, analysis_id, timeout_seconds, poll_interval)
            verdict = self._verdict_from_analysis(report, str(path), file_hash)
            verdict["source"] = "uploaded_file"
            return verdict

    async def _get_existing_report(self, session: aiohttp.ClientSession, file_hash: str) -> dict[str, Any] | None:
        async with session.get(f"{self.BASE_URL}/files/{file_hash}") as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            payload = await response.json()
            return payload.get("data")

    async def _upload_file(self, session: aiohttp.ClientSession, path: Path) -> str:
        form = aiohttp.FormData()
        fh = path.open("rb")
        try:
            form.add_field("file", fh, filename=path.name)
            async with session.post(f"{self.BASE_URL}/files", data=form) as response:
                response.raise_for_status()
                payload = await response.json()
                return payload["data"]["id"]
        finally:
            fh.close()

    async def _poll_analysis(
        self,
        session: aiohttp.ClientSession,
        analysis_id: str,
        timeout_seconds: int,
        poll_interval: int,
    ) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while True:
            async with session.get(f"{self.BASE_URL}/analyses/{analysis_id}") as response:
                response.raise_for_status()
                payload = await response.json()
                data = payload["data"]
                status = data.get("attributes", {}).get("status")
                if status == "completed":
                    return data

            if loop.time() >= deadline:
                raise TimeoutError("VirusTotal no completó el análisis a tiempo.")
            await asyncio.sleep(poll_interval)

    def _verdict_from_report(self, data: dict[str, Any], file_path: str, file_hash: str) -> dict[str, Any]:
        stats = data.get("attributes", {}).get("last_analysis_stats", {})
        return self._build_verdict(file_path=file_path, file_hash=file_hash, stats=stats, raw_status="completed")

    def _verdict_from_analysis(self, data: dict[str, Any], file_path: str, file_hash: str) -> dict[str, Any]:
        stats = data.get("attributes", {}).get("stats", {})
        return self._build_verdict(file_path=file_path, file_hash=file_hash, stats=stats, raw_status="completed")

    def _build_verdict(
        self,
        *,
        file_path: str,
        file_hash: str,
        stats: dict[str, Any],
        raw_status: str,
    ) -> dict[str, Any]:
        malicious = int(stats.get("malicious", 0) or 0)
        suspicious = int(stats.get("suspicious", 0) or 0)
        harmless = int(stats.get("harmless", 0) or 0)
        undetected = int(stats.get("undetected", 0) or 0)
        trusted = malicious == 0 and suspicious == 0 and (harmless > 0 or undetected > 0)
        return {
            "configured": True,
            "status": raw_status,
            "trusted": trusted,
            "file_path": file_path,
            "sha256": file_hash,
            "stats": {
                "malicious": malicious,
                "suspicious": suspicious,
                "harmless": harmless,
                "undetected": undetected,
            },
        }

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
