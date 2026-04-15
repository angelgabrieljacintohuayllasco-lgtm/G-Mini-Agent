"""
Auto-Update & Distribution — Version check, download, channel management,
and rollback for the G-Mini Agent application.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"


class UpdateStatus(str, Enum):
    IDLE = "idle"
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    READY = "ready"
    FAILED = "failed"


class AutoUpdater:
    """Manages application version checking, channels, and update history."""

    CURRENT_VERSION = "1.0.0"

    def __init__(self) -> None:
        db_path = config.get("updater", "db_path") or "data/updater.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._channel = UpdateChannel(config.get("updater", "channel") or "stable")
        self._auto_check = config.get("updater", "auto_check") is not False
        self._check_interval = float(config.get("updater", "check_interval_hours") or 24) * 3600
        self._status = UpdateStatus.IDLE
        self._last_check = 0.0
        self._latest_version: str | None = None
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS update_history (
                    update_id       TEXT PRIMARY KEY,
                    from_version    TEXT NOT NULL,
                    to_version      TEXT NOT NULL,
                    channel         TEXT NOT NULL,
                    status          TEXT NOT NULL,
                    timestamp       REAL NOT NULL,
                    notes           TEXT
                )
            """)
            conn.commit()

    def get_current_version(self) -> str:
        return self.CURRENT_VERSION

    def get_channel(self) -> str:
        return self._channel.value

    def set_channel(self, channel: str) -> dict:
        try:
            self._channel = UpdateChannel(channel)
            return {"channel": self._channel.value}
        except ValueError:
            return {"error": f"Invalid channel: {channel}. Use 'stable' or 'beta'."}

    def check_for_updates(self, update_url: str | None = None) -> dict:
        """
        Check if a new version is available.
        In production this would query a remote server. This implementation
        provides the structure for integration.
        """
        self._status = UpdateStatus.CHECKING
        self._last_check = time.time()

        # In production: fetch JSON from update_url or config endpoint
        # For now, we simulate the structure
        result = {
            "current_version": self.CURRENT_VERSION,
            "channel": self._channel.value,
            "status": "up_to_date",
            "checked_at": self._last_check,
        }

        # When update_url is provided, you'd fetch and compare versions here
        if update_url:
            result["update_url"] = update_url
            result["status"] = "checked"

        self._status = UpdateStatus.IDLE
        return result

    def record_update(
        self,
        from_version: str,
        to_version: str,
        status: str = "success",
        notes: str | None = None,
    ) -> dict:
        """Record an update in the history."""
        update_id = str(uuid.uuid4())[:10]
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO update_history
                (update_id, from_version, to_version, channel, status, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (update_id, from_version, to_version, self._channel.value,
                 status, time.time(), notes),
            )
            conn.commit()
        return {"update_id": update_id, "status": status}

    def get_update_history(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM update_history ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def rollback_info(self) -> dict:
        """Get info about the last successful update for potential rollback."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM update_history WHERE status = 'success' ORDER BY timestamp DESC LIMIT 1",
            ).fetchone()
        if row:
            return {
                "can_rollback": True,
                "last_update": dict(row),
                "rollback_version": row["from_version"],
            }
        return {"can_rollback": False}

    def get_status(self) -> dict:
        return {
            "current_version": self.CURRENT_VERSION,
            "channel": self._channel.value,
            "status": self._status.value,
            "auto_check": self._auto_check,
            "last_check": self._last_check,
            "latest_available": self._latest_version,
        }


# ═══════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════

_updater: AutoUpdater | None = None


def get_auto_updater() -> AutoUpdater:
    global _updater
    if _updater is None:
        _updater = AutoUpdater()
    return _updater
