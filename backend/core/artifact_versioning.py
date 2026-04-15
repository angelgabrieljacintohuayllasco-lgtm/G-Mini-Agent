"""
Artifact Versioning — Version control for workflows, macros,
prompts, policies, and router configs.

Stages: draft → staging → prod
Retains up to N versions per artifact with full diff history.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


class ArtifactVersioning:
    """Tracks versioned artifacts with stage promotion."""

    STAGES = ("draft", "staging", "prod")
    DEFAULT_MAX_VERSIONS = 50

    def __init__(self) -> None:
        db_path = config.get("versioning", "db_path") or "data/versioning.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._max = int(config.get("versioning", "max_versions") or self.DEFAULT_MAX_VERSIONS)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    version_id    TEXT PRIMARY KEY,
                    artifact_id   TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    stage         TEXT NOT NULL DEFAULT 'draft',
                    version       INTEGER NOT NULL DEFAULT 1,
                    content       TEXT NOT NULL,
                    metadata      TEXT NOT NULL DEFAULT '{}',
                    author        TEXT NOT NULL DEFAULT 'system',
                    message       TEXT NOT NULL DEFAULT '',
                    created_at    REAL NOT NULL,
                    UNIQUE(artifact_id, version)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_av_artifact ON artifact_versions(artifact_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_av_type ON artifact_versions(artifact_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_av_stage ON artifact_versions(stage)")
            conn.commit()

    # ── Create version ───────────────────────────────────────────────

    def create_version(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str | dict,
        author: str = "system",
        message: str = "",
        stage: str = "draft",
    ) -> dict:
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)

        now = time.time()
        version_id = str(uuid.uuid4())[:12]

        with sqlite3.connect(str(self._db_path)) as conn:
            # Get next version number
            row = conn.execute(
                "SELECT MAX(version) FROM artifact_versions WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
            next_ver = (row[0] or 0) + 1

            conn.execute(
                """INSERT INTO artifact_versions
                (version_id, artifact_id, artifact_type, stage, version, content,
                 metadata, author, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (version_id, artifact_id, artifact_type, stage, next_ver,
                 content, "{}", author, message, now),
            )
            conn.commit()

        # Evict old versions
        self._evict(artifact_id)

        return {
            "version_id": version_id,
            "artifact_id": artifact_id,
            "version": next_ver,
            "stage": stage,
        }

    # ── Promote stage ────────────────────────────────────────────────

    def promote(self, version_id: str, target_stage: str) -> dict | None:
        if target_stage not in self.STAGES:
            return None
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
            ).fetchone()
            if not row:
                return None

            current_idx = self.STAGES.index(row["stage"])
            target_idx = self.STAGES.index(target_stage)
            if target_idx <= current_idx:
                return {"error": f"Cannot demote from {row['stage']} to {target_stage}"}

            conn.execute(
                "UPDATE artifact_versions SET stage = ? WHERE version_id = ?",
                (target_stage, version_id),
            )
            conn.commit()

        return {"ok": True, "version_id": version_id, "stage": target_stage}

    # ── Rollback ─────────────────────────────────────────────────────

    def rollback_to(self, artifact_id: str, version: int) -> dict | None:
        """Create a new version that copies content from a previous version."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM artifact_versions WHERE artifact_id = ? AND version = ?",
                (artifact_id, version),
            ).fetchone()
            if not row:
                return None

        return self.create_version(
            artifact_id=artifact_id,
            artifact_type=row["artifact_type"],
            content=row["content"],
            author="rollback",
            message=f"Rollback to version {version}",
            stage="draft",
        )

    # ── Query ────────────────────────────────────────────────────────

    def get_version(self, version_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def get_latest(self, artifact_id: str, stage: str | None = None) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if stage:
                row = conn.execute(
                    "SELECT * FROM artifact_versions WHERE artifact_id = ? AND stage = ? ORDER BY version DESC LIMIT 1",
                    (artifact_id, stage),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM artifact_versions WHERE artifact_id = ? ORDER BY version DESC LIMIT 1",
                    (artifact_id,),
                ).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_versions(
        self,
        artifact_id: str | None = None,
        artifact_type: str | None = None,
        stage: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        query = "SELECT * FROM artifact_versions"
        params: list[Any] = []
        conditions = []
        if artifact_id:
            conditions.append("artifact_id = ?")
            params.append(artifact_id)
        if artifact_type:
            conditions.append("artifact_type = ?")
            params.append(artifact_type)
        if stage:
            conditions.append("stage = ?")
            params.append(stage)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r, include_content=False) for r in rows]

    def diff_versions(self, artifact_id: str, v1: int, v2: int) -> dict | None:
        """Simple diff between two versions of the same artifact."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            r1 = conn.execute(
                "SELECT * FROM artifact_versions WHERE artifact_id = ? AND version = ?",
                (artifact_id, v1),
            ).fetchone()
            r2 = conn.execute(
                "SELECT * FROM artifact_versions WHERE artifact_id = ? AND version = ?",
                (artifact_id, v2),
            ).fetchone()

        if not r1 or not r2:
            return None

        return {
            "artifact_id": artifact_id,
            "v1": v1,
            "v2": v2,
            "v1_stage": r1["stage"],
            "v2_stage": r2["stage"],
            "v1_author": r1["author"],
            "v2_author": r2["author"],
            "content_changed": r1["content"] != r2["content"],
            "v1_length": len(r1["content"]),
            "v2_length": len(r2["content"]),
        }

    # ── Helpers ──────────────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row, include_content: bool = True) -> dict:
        d: dict[str, Any] = {
            "version_id": row["version_id"],
            "artifact_id": row["artifact_id"],
            "artifact_type": row["artifact_type"],
            "stage": row["stage"],
            "version": row["version"],
            "author": row["author"],
            "message": row["message"],
            "created_at": row["created_at"],
        }
        if include_content:
            d["content"] = row["content"]
        return d

    def _evict(self, artifact_id: str) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM artifact_versions WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()[0]
            if count > self._max:
                excess = count - self._max
                conn.execute(
                    """DELETE FROM artifact_versions WHERE version_id IN (
                        SELECT version_id FROM artifact_versions
                        WHERE artifact_id = ? AND stage = 'draft'
                        ORDER BY version ASC LIMIT ?
                    )""",
                    (artifact_id, excess),
                )
                conn.commit()


# ── Singleton ────────────────────────────────────────────────────────────

_versioning: ArtifactVersioning | None = None


def get_versioning() -> ArtifactVersioning:
    global _versioning
    if _versioning is None:
        _versioning = ArtifactVersioning()
    return _versioning
