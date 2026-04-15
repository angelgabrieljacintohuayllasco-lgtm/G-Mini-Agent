"""
Offline Mode + Sync — Connectivity detection, graceful degradation,
multi-device sync, and skill deprecation lifecycle.
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


# ═══════════════════════════════════════════════════════════════════════
# Connectivity & Offline Mode
# ═══════════════════════════════════════════════════════════════════════

class ConnectivityState(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


# Capabilities available in each state
STATE_CAPABILITIES: dict[str, list[str]] = {
    ConnectivityState.ONLINE.value: [
        "cloud_llm", "local_llm", "tts_cloud", "tts_local",
        "stt_cloud", "stt_local", "web_search", "api_calls",
        "email", "gateway", "sync", "vision_cloud", "vision_local",
    ],
    ConnectivityState.DEGRADED.value: [
        "local_llm", "tts_local", "stt_local", "vision_local",
        "local_files", "local_skills", "automation_local",
    ],
    ConnectivityState.OFFLINE.value: [
        "local_llm", "tts_local", "stt_local", "vision_local",
        "local_files", "local_skills",
    ],
}


class OfflineManager:
    """Manages connectivity state transitions and capability availability."""

    def __init__(self) -> None:
        self._state = ConnectivityState.ONLINE
        self._last_check = 0.0
        self._check_interval = float(config.get("offline", "check_interval") or 30)
        self._transition_log: list[dict] = []

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def capabilities(self) -> list[str]:
        return STATE_CAPABILITIES.get(self._state.value, [])

    def check_connectivity(self) -> dict:
        """Check current connectivity (lightweight)."""
        import socket
        now = time.time()

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            new_state = ConnectivityState.ONLINE
        except OSError:
            # Try local network
            try:
                socket.create_connection(("192.168.1.1", 80), timeout=2)
                new_state = ConnectivityState.DEGRADED
            except OSError:
                new_state = ConnectivityState.OFFLINE

        if new_state != self._state:
            self._log_transition(self._state, new_state)
            self._state = new_state

        self._last_check = now
        return {
            "state": self._state.value,
            "capabilities": self.capabilities,
            "last_check": now,
        }

    def force_state(self, state: str) -> dict:
        """Manually override connectivity state."""
        try:
            new_state = ConnectivityState(state)
        except ValueError:
            return {"error": f"Invalid state: {state}"}

        if new_state != self._state:
            self._log_transition(self._state, new_state)
            self._state = new_state

        return {"state": self._state.value, "capabilities": self.capabilities}

    def is_capable(self, capability: str) -> bool:
        return capability in self.capabilities

    def get_status(self) -> dict:
        return {
            "state": self._state.value,
            "capabilities": self.capabilities,
            "last_check": self._last_check,
            "transitions": self._transition_log[-10:],
        }

    def _log_transition(self, old: ConnectivityState, new: ConnectivityState) -> None:
        entry = {
            "from": old.value,
            "to": new.value,
            "timestamp": time.time(),
        }
        self._transition_log.append(entry)
        logger.info(f"[Connectivity] {old.value} → {new.value}")


# ═══════════════════════════════════════════════════════════════════════
# Multi-device Sync
# ═══════════════════════════════════════════════════════════════════════

class SyncManager:
    """Sync data between devices with conflict resolution."""

    def __init__(self) -> None:
        db_path = config.get("sync", "db_path") or "data/sync.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._device_id = config.get("sync", "device_id") or str(uuid.uuid4())[:8]
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sync_items (
                    item_id     TEXT PRIMARY KEY,
                    item_type   TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    device_id   TEXT NOT NULL,
                    version     INTEGER NOT NULL DEFAULT 1,
                    timestamp   REAL NOT NULL,
                    synced      INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sync_type ON sync_items(item_type);
                CREATE INDEX IF NOT EXISTS idx_sync_synced ON sync_items(synced);

                CREATE TABLE IF NOT EXISTS sync_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    item_id     TEXT NOT NULL,
                    local_content TEXT NOT NULL,
                    remote_content TEXT NOT NULL,
                    resolution  TEXT,
                    timestamp   REAL NOT NULL,
                    resolved    INTEGER NOT NULL DEFAULT 0
                );
            """)
            conn.commit()

    def add_item(
        self,
        item_type: str,
        content: str | dict,
        item_id: str | None = None,
    ) -> dict:
        """Add or update an item for sync."""
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)

        item_id = item_id or str(uuid.uuid4())[:12]
        now = time.time()

        with sqlite3.connect(str(self._db_path)) as conn:
            existing = conn.execute(
                "SELECT version FROM sync_items WHERE item_id = ?", (item_id,)
            ).fetchone()
            version = (existing[0] + 1) if existing else 1

            conn.execute(
                """INSERT OR REPLACE INTO sync_items
                (item_id, item_type, content, device_id, version, timestamp, synced)
                VALUES (?, ?, ?, ?, ?, ?, 0)""",
                (item_id, item_type, content, self._device_id, version, now),
            )
            conn.commit()

        return {"item_id": item_id, "version": version}

    def get_pending(self, limit: int = 100) -> list[dict]:
        """Get items that haven't been synced yet."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sync_items WHERE synced = 0 ORDER BY timestamp ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_synced(self, item_ids: list[str]) -> int:
        with sqlite3.connect(str(self._db_path)) as conn:
            count = 0
            for item_id in item_ids:
                c = conn.execute(
                    "UPDATE sync_items SET synced = 1 WHERE item_id = ?", (item_id,)
                ).rowcount
                count += c
            conn.commit()
        return count

    def receive_remote(self, items: list[dict]) -> dict:
        """Receive items from remote device with conflict detection."""
        applied = 0
        conflicts = 0

        with sqlite3.connect(str(self._db_path)) as conn:
            for item in items:
                local = conn.execute(
                    "SELECT * FROM sync_items WHERE item_id = ?",
                    (item["item_id"],),
                ).fetchone()

                if local:
                    # Conflict resolution: newer wins
                    if item.get("timestamp", 0) > (local[5] if local else 0):  # timestamp column
                        conn.execute(
                            """INSERT OR REPLACE INTO sync_items
                            (item_id, item_type, content, device_id, version, timestamp, synced)
                            VALUES (?, ?, ?, ?, ?, ?, 1)""",
                            (item["item_id"], item["item_type"], item["content"],
                             item.get("device_id", "remote"), item.get("version", 1),
                             item.get("timestamp", time.time())),
                        )
                        applied += 1
                    else:
                        # Record conflict
                        conn.execute(
                            """INSERT INTO sync_conflicts
                            (conflict_id, item_id, local_content, remote_content, timestamp)
                            VALUES (?, ?, ?, ?, ?)""",
                            (str(uuid.uuid4())[:10], item["item_id"],
                             local[2] if local else "",  # content column
                             item.get("content", ""), time.time()),
                        )
                        conflicts += 1
                else:
                    conn.execute(
                        """INSERT INTO sync_items
                        (item_id, item_type, content, device_id, version, timestamp, synced)
                        VALUES (?, ?, ?, ?, ?, ?, 1)""",
                        (item["item_id"], item["item_type"], item["content"],
                         item.get("device_id", "remote"), item.get("version", 1),
                         item.get("timestamp", time.time())),
                    )
                    applied += 1

            conn.commit()

        return {"applied": applied, "conflicts": conflicts}

    def get_conflicts(self, resolved: bool = False) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sync_conflicts WHERE resolved = ? ORDER BY timestamp DESC",
                (int(resolved),),
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "UPDATE sync_conflicts SET resolved = 1, resolution = ? WHERE conflict_id = ?",
                (resolution, conflict_id),
            ).rowcount
            conn.commit()
            return c > 0

    def get_status(self) -> dict:
        with sqlite3.connect(str(self._db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM sync_items").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM sync_items WHERE synced = 0").fetchone()[0]
            conflicts = conn.execute("SELECT COUNT(*) FROM sync_conflicts WHERE resolved = 0").fetchone()[0]
        return {
            "device_id": self._device_id,
            "total_items": total,
            "pending_sync": pending,
            "unresolved_conflicts": conflicts,
        }


# ═══════════════════════════════════════════════════════════════════════
# Skill Deprecation Lifecycle
# ═══════════════════════════════════════════════════════════════════════

class SkillDeprecation:
    """Manages skill lifecycle: active → review → archived."""

    INACTIVE_DAYS_THRESHOLD = 60
    ARCHIVE_DAYS_AFTER_REVIEW = 7
    BROKEN_DAYS_THRESHOLD = 14

    def __init__(self) -> None:
        db_path = config.get("sync", "db_path") or "data/sync.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_lifecycle (
                    skill_id        TEXT PRIMARY KEY,
                    skill_name      TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'active',
                    last_used       REAL,
                    success_rate    REAL NOT NULL DEFAULT 1.0,
                    total_uses      INTEGER NOT NULL DEFAULT 0,
                    review_started  REAL,
                    archived_at     REAL,
                    reason          TEXT
                )
            """)
            conn.commit()

    def register_skill(self, skill_id: str, skill_name: str) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR IGNORE INTO skill_lifecycle
                (skill_id, skill_name, status, last_used)
                VALUES (?, ?, 'active', ?)""",
                (skill_id, skill_name, time.time()),
            )
            conn.commit()

    def record_use(self, skill_id: str, success: bool) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT total_uses, success_rate FROM skill_lifecycle WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
            if row:
                total = row[0] + 1
                old_rate = row[1]
                new_rate = old_rate * 0.9 + (1.0 if success else 0.0) * 0.1
                conn.execute(
                    "UPDATE skill_lifecycle SET last_used = ?, total_uses = ?, success_rate = ? WHERE skill_id = ?",
                    (time.time(), total, new_rate, skill_id),
                )
                conn.commit()

    def evaluate_lifecycle(self) -> list[dict]:
        """Check all skills for deprecation criteria."""
        now = time.time()
        changes: list[dict] = []

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            skills = conn.execute("SELECT * FROM skill_lifecycle WHERE status != 'archived'").fetchall()

            for s in skills:
                skill_id = s["skill_id"]
                status = s["status"]
                last_used = s["last_used"] or 0
                days_inactive = (now - last_used) / 86400 if last_used else 999

                if status == "active":
                    # Check for review
                    if days_inactive >= self.INACTIVE_DAYS_THRESHOLD:
                        conn.execute(
                            "UPDATE skill_lifecycle SET status = 'review', review_started = ?, reason = ? WHERE skill_id = ?",
                            (now, f"Inactive for {int(days_inactive)} days", skill_id),
                        )
                        changes.append({"skill_id": skill_id, "action": "moved_to_review", "reason": "inactive"})
                    elif s["success_rate"] < 0.5 and s["total_uses"] >= 5:
                        conn.execute(
                            "UPDATE skill_lifecycle SET status = 'review', review_started = ?, reason = ? WHERE skill_id = ?",
                            (now, f"Low success rate: {s['success_rate']:.0%}", skill_id),
                        )
                        changes.append({"skill_id": skill_id, "action": "moved_to_review", "reason": "low_success"})

                elif status == "review":
                    review_days = (now - (s["review_started"] or now)) / 86400
                    if review_days >= self.ARCHIVE_DAYS_AFTER_REVIEW:
                        conn.execute(
                            "UPDATE skill_lifecycle SET status = 'archived', archived_at = ? WHERE skill_id = ?",
                            (now, skill_id),
                        )
                        changes.append({"skill_id": skill_id, "action": "archived", "reason": "no_response"})

            conn.commit()

        return changes

    def reactivate(self, skill_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "UPDATE skill_lifecycle SET status = 'active', review_started = NULL, archived_at = NULL, reason = NULL WHERE skill_id = ?",
                (skill_id,),
            ).rowcount
            conn.commit()
            return c > 0

    def list_skills(self, status: str | None = None) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    "SELECT * FROM skill_lifecycle WHERE status = ? ORDER BY last_used DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM skill_lifecycle ORDER BY status, last_used DESC").fetchall()
        return [dict(r) for r in rows]

    def get_health_report(self) -> dict:
        with sqlite3.connect(str(self._db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM skill_lifecycle").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM skill_lifecycle WHERE status = 'active'").fetchone()[0]
            review = conn.execute("SELECT COUNT(*) FROM skill_lifecycle WHERE status = 'review'").fetchone()[0]
            archived = conn.execute("SELECT COUNT(*) FROM skill_lifecycle WHERE status = 'archived'").fetchone()[0]
        return {
            "total_skills": total,
            "active": active,
            "in_review": review,
            "archived": archived,
            "health_pct": round((active / total * 100) if total else 100, 1),
        }


# ═══════════════════════════════════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════════════════════════════════

_offline: OfflineManager | None = None
_sync: SyncManager | None = None
_deprecation: SkillDeprecation | None = None


def get_offline_manager() -> OfflineManager:
    global _offline
    if _offline is None:
        _offline = OfflineManager()
    return _offline


def get_sync_manager() -> SyncManager:
    global _sync
    if _sync is None:
        _sync = SyncManager()
    return _sync


def get_skill_deprecation() -> SkillDeprecation:
    global _deprecation
    if _deprecation is None:
        _deprecation = SkillDeprecation()
    return _deprecation
