"""
Rollback / Undo System.

Takes snapshots before critical actions and allows rolling back to previous states.
Tracks: files modified, commands executed, application state.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


@dataclass
class Snapshot:
    snapshot_id: str
    description: str
    action_type: str
    files_backed_up: list[dict[str, str]]  # [{"original": path, "backup": backup_path}]
    commands_log: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    rolled_back: bool = False
    rolled_back_at: float | None = None


class RollbackManager:
    """Manages snapshots and rollback of critical agent actions."""

    MAX_SNAPSHOTS = 20

    def __init__(self) -> None:
        db_path = config.get("rollback", "db_path") or "data/rollback.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._backup_dir = Path(config.get("rollback", "backup_dir") or "data/rollback_backups")
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id    TEXT PRIMARY KEY,
                    description    TEXT NOT NULL DEFAULT '',
                    action_type    TEXT NOT NULL,
                    files_json     TEXT NOT NULL DEFAULT '[]',
                    commands_json  TEXT NOT NULL DEFAULT '[]',
                    metadata       TEXT NOT NULL DEFAULT '{}',
                    created_at     REAL NOT NULL,
                    rolled_back    INTEGER NOT NULL DEFAULT 0,
                    rolled_back_at REAL
                )
            """)
            conn.commit()

    # ── Create snapshot ──────────────────────────────────────────────

    def create_snapshot(
        self,
        action_type: str,
        files_to_backup: list[str] | None = None,
        commands: list[str] | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a snapshot before a critical action. Returns snapshot_id."""
        snapshot_id = str(uuid.uuid4())[:12]
        now = time.time()
        files_backed_up = []

        # Backup files
        if files_to_backup:
            snapshot_dir = self._backup_dir / snapshot_id
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            for filepath in files_to_backup:
                src = Path(filepath)
                if src.exists() and src.is_file():
                    backup_name = src.name
                    backup_path = snapshot_dir / backup_name
                    # Handle name collisions
                    counter = 0
                    while backup_path.exists():
                        counter += 1
                        backup_path = snapshot_dir / f"{src.stem}_{counter}{src.suffix}"
                    try:
                        shutil.copy2(str(src), str(backup_path))
                        files_backed_up.append({
                            "original": str(src),
                            "backup": str(backup_path),
                        })
                    except Exception as e:
                        logger.error(f"Snapshot backup failed for {src}: {e}")

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO snapshots
                (snapshot_id, description, action_type, files_json, commands_json, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id, description, action_type,
                    json.dumps(files_backed_up),
                    json.dumps(commands or []),
                    json.dumps(metadata or {}),
                    now,
                ),
            )
            conn.commit()

        logger.info(f"Snapshot created: {snapshot_id} ({len(files_backed_up)} files backed up)")
        self._evict_old()
        return snapshot_id

    # ── Rollback ─────────────────────────────────────────────────────

    def rollback(self, snapshot_id: str) -> dict:
        """Rollback to a previous snapshot."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchone()

        if not row:
            return {"ok": False, "error": "Snapshot not found"}

        if row["rolled_back"]:
            return {"ok": False, "error": "Already rolled back"}

        files_data = json.loads(row["files_json"])
        restored = []
        errors = []

        for entry in files_data:
            backup_path = Path(entry["backup"])
            original_path = Path(entry["original"])
            if not backup_path.exists():
                errors.append(f"Backup file missing: {backup_path}")
                continue
            try:
                original_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(backup_path), str(original_path))
                restored.append(str(original_path))
            except Exception as e:
                errors.append(f"Failed to restore {original_path}: {e}")

        # Mark as rolled back
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE snapshots SET rolled_back = 1, rolled_back_at = ? WHERE snapshot_id = ?",
                (now, snapshot_id),
            )
            conn.commit()

        logger.info(f"Rollback {snapshot_id}: {len(restored)} files restored, {len(errors)} errors")

        return {
            "ok": len(errors) == 0,
            "snapshot_id": snapshot_id,
            "files_restored": restored,
            "errors": errors,
        }

    # ── Query ────────────────────────────────────────────────────────

    def list_snapshots(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM snapshots ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["files_json"] = json.loads(d["files_json"])
                d["commands_json"] = json.loads(d["commands_json"])
                d["metadata"] = json.loads(d["metadata"])
                d["rolled_back"] = bool(d["rolled_back"])
                result.append(d)
            return result

    def get_snapshot(self, snapshot_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["files_json"] = json.loads(d["files_json"])
            d["commands_json"] = json.loads(d["commands_json"])
            d["metadata"] = json.loads(d["metadata"])
            d["rolled_back"] = bool(d["rolled_back"])
            return d

    def delete_snapshot(self, snapshot_id: str) -> bool:
        # Remove backup files
        snapshot_dir = self._backup_dir / snapshot_id
        if snapshot_dir.exists():
            shutil.rmtree(str(snapshot_dir), ignore_errors=True)

        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
            conn.commit()
            return cur.rowcount > 0

    def _evict_old(self) -> None:
        """Remove oldest snapshots beyond max limit."""
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()
            count = row[0] if row else 0
            if count <= self.MAX_SNAPSHOTS:
                return
            # Get IDs to remove
            rows = conn.execute(
                "SELECT snapshot_id FROM snapshots ORDER BY created_at ASC LIMIT ?",
                (count - self.MAX_SNAPSHOTS,),
            ).fetchall()
            for r in rows:
                sid = r[0]
                snap_dir = self._backup_dir / sid
                if snap_dir.exists():
                    shutil.rmtree(str(snap_dir), ignore_errors=True)
                conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (sid,))
            conn.commit()


# ── Singleton ────────────────────────────────────────────────────────────

_rollback: RollbackManager | None = None


def get_rollback() -> RollbackManager:
    global _rollback
    if _rollback is None:
        _rollback = RollbackManager()
    return _rollback
