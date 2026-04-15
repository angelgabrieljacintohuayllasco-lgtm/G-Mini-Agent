"""
Analytics Engine — Task metrics, token usage tracking, error history,
performance summaries, and weekly report generation.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


@dataclass
class TaskMetric:
    task_id: str
    task_type: str
    status: str                 # completed / failed
    duration_seconds: float
    tokens_in: int
    tokens_out: int
    provider: str
    model: str
    error: str | None
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 2),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "provider": self.provider,
            "model": self.model,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class AnalyticsEngine:
    """Collects and aggregates task, token, and error metrics."""

    def __init__(self) -> None:
        db_path = config.get("analytics", "db_path") or "data/analytics.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS task_metrics (
                    task_id          TEXT PRIMARY KEY,
                    task_type        TEXT NOT NULL,
                    status           TEXT NOT NULL,
                    duration_seconds REAL NOT NULL DEFAULT 0,
                    tokens_in        INTEGER NOT NULL DEFAULT 0,
                    tokens_out       INTEGER NOT NULL DEFAULT 0,
                    provider         TEXT NOT NULL DEFAULT '',
                    model            TEXT NOT NULL DEFAULT '',
                    error            TEXT,
                    timestamp        REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_ts ON task_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_metrics_provider ON task_metrics(provider);
                CREATE INDEX IF NOT EXISTS idx_metrics_status ON task_metrics(status);

                CREATE TABLE IF NOT EXISTS token_usage (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider    TEXT NOT NULL,
                    model       TEXT NOT NULL,
                    tokens_in   INTEGER NOT NULL DEFAULT 0,
                    tokens_out  INTEGER NOT NULL DEFAULT 0,
                    cost_usd    REAL NOT NULL DEFAULT 0,
                    timestamp   REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_token_ts ON token_usage(timestamp);
            """)
            conn.commit()

    # ── Recording ────────────────────────────────────────────────────

    def record_task(
        self,
        task_id: str,
        task_type: str,
        status: str,
        duration_seconds: float = 0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        provider: str = "",
        model: str = "",
        error: str | None = None,
    ) -> None:
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO task_metrics
                (task_id, task_type, status, duration_seconds, tokens_in, tokens_out,
                 provider, model, error, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, task_type, status, duration_seconds,
                 tokens_in, tokens_out, provider, model, error, now),
            )
            conn.commit()

    def record_token_usage(
        self,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float = 0.0,
    ) -> None:
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO token_usage
                (provider, model, tokens_in, tokens_out, cost_usd, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (provider, model, tokens_in, tokens_out, cost_usd, now),
            )
            conn.commit()

    # ── Queries ──────────────────────────────────────────────────────

    def get_task_stats(self, since: float | None = None) -> dict:
        """Get aggregated task statistics."""
        since = since or 0
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row

            total = conn.execute(
                "SELECT COUNT(*) as c FROM task_metrics WHERE timestamp >= ?", (since,)
            ).fetchone()["c"]

            completed = conn.execute(
                "SELECT COUNT(*) as c FROM task_metrics WHERE status = 'completed' AND timestamp >= ?",
                (since,),
            ).fetchone()["c"]

            failed = conn.execute(
                "SELECT COUNT(*) as c FROM task_metrics WHERE status = 'failed' AND timestamp >= ?",
                (since,),
            ).fetchone()["c"]

            avg_dur = conn.execute(
                "SELECT AVG(duration_seconds) as v FROM task_metrics WHERE status = 'completed' AND timestamp >= ?",
                (since,),
            ).fetchone()["v"] or 0

            # By type
            by_type_rows = conn.execute(
                """SELECT task_type, COUNT(*) as cnt,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as ok,
                   AVG(duration_seconds) as avg_dur
                   FROM task_metrics WHERE timestamp >= ?
                   GROUP BY task_type ORDER BY cnt DESC""",
                (since,),
            ).fetchall()

        by_type = [
            {
                "task_type": r["task_type"],
                "count": r["cnt"],
                "success": r["ok"],
                "avg_duration": round(r["avg_dur"] or 0, 2),
            }
            for r in by_type_rows
        ]

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round((completed / total * 100) if total else 0, 1),
            "avg_duration_seconds": round(avg_dur, 2),
            "by_type": by_type,
        }

    def get_token_stats(self, since: float | None = None) -> dict:
        """Get token usage statistics."""
        since = since or 0
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row

            totals = conn.execute(
                """SELECT COALESCE(SUM(tokens_in), 0) as ti,
                          COALESCE(SUM(tokens_out), 0) as to_,
                          COALESCE(SUM(cost_usd), 0) as cost
                   FROM token_usage WHERE timestamp >= ?""",
                (since,),
            ).fetchone()

            by_provider = conn.execute(
                """SELECT provider, model,
                   SUM(tokens_in) as ti, SUM(tokens_out) as to_,
                   SUM(cost_usd) as cost, COUNT(*) as calls
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY provider, model ORDER BY cost DESC""",
                (since,),
            ).fetchall()

        return {
            "total_tokens_in": totals["ti"],
            "total_tokens_out": totals["to_"],
            "total_cost_usd": round(totals["cost"], 4),
            "by_provider": [
                {
                    "provider": r["provider"],
                    "model": r["model"],
                    "tokens_in": r["ti"],
                    "tokens_out": r["to_"],
                    "cost_usd": round(r["cost"], 4),
                    "calls": r["calls"],
                }
                for r in by_provider
            ],
        }

    def get_error_history(self, limit: int = 50, since: float | None = None) -> list[dict]:
        since = since or 0
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT task_id, task_type, error, provider, model, timestamp
                   FROM task_metrics WHERE status = 'failed' AND error IS NOT NULL
                   AND timestamp >= ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (since, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_time_distribution(self, since: float | None = None) -> list[dict]:
        """Time distribution by task type."""
        since = since or 0
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT task_type,
                   SUM(duration_seconds) as total_seconds,
                   COUNT(*) as count
                   FROM task_metrics WHERE timestamp >= ?
                   GROUP BY task_type ORDER BY total_seconds DESC""",
                (since,),
            ).fetchall()
        total_time = sum(r["total_seconds"] or 0 for r in rows)
        return [
            {
                "task_type": r["task_type"],
                "total_seconds": round(r["total_seconds"] or 0, 1),
                "count": r["count"],
                "pct": round(((r["total_seconds"] or 0) / total_time * 100) if total_time else 0, 1),
            }
            for r in rows
        ]

    def get_activity_timeline(self, hours: int = 24) -> list[dict]:
        """Hourly activity breakdown for the last N hours."""
        cutoff = time.time() - (hours * 3600)
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT
                    CAST((timestamp - ?) / 3600 AS INTEGER) as hour_offset,
                    COUNT(*) as count,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as ok,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as fail
                   FROM task_metrics WHERE timestamp >= ?
                   GROUP BY hour_offset ORDER BY hour_offset""",
                (cutoff, cutoff),
            ).fetchall()
        return [
            {
                "hour_offset": r["hour_offset"],
                "total": r["count"],
                "completed": r["ok"],
                "failed": r["fail"],
            }
            for r in rows
        ]

    def generate_weekly_report(self) -> dict:
        """Generate a summary report for the last 7 days."""
        since = time.time() - (7 * 86400)
        return {
            "period": "last_7_days",
            "generated_at": time.time(),
            "tasks": self.get_task_stats(since),
            "tokens": self.get_token_stats(since),
            "errors": self.get_error_history(limit=20, since=since),
            "time_distribution": self.get_time_distribution(since),
            "activity_timeline": self.get_activity_timeline(hours=168),  # 7 days
        }

    # ── Dashboard summary ────────────────────────────────────────────

    def get_dashboard(self) -> dict:
        """Consolidated executive dashboard."""
        now = time.time()
        last_24h = now - 86400
        last_7d = now - 7 * 86400

        return {
            "summary_24h": self.get_task_stats(last_24h),
            "summary_7d": self.get_task_stats(last_7d),
            "tokens_24h": self.get_token_stats(last_24h),
            "tokens_7d": self.get_token_stats(last_7d),
            "recent_errors": self.get_error_history(limit=10, since=last_24h),
            "activity_24h": self.get_activity_timeline(24),
        }

    def cleanup_old(self, days: int = 90) -> int:
        cutoff = time.time() - (days * 86400)
        with sqlite3.connect(str(self._db_path)) as conn:
            c1 = conn.execute("DELETE FROM task_metrics WHERE timestamp < ?", (cutoff,)).rowcount
            c2 = conn.execute("DELETE FROM token_usage WHERE timestamp < ?", (cutoff,)).rowcount
            conn.commit()
        return c1 + c2


# ── Singleton ────────────────────────────────────────────────────────────

_analytics: AnalyticsEngine | None = None


def get_analytics() -> AnalyticsEngine:
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsEngine()
    return _analytics
