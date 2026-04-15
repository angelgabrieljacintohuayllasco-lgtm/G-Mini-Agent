"""
Causal Alerts Engine — Real-time business metrics monitoring
with temporal correlation for root cause detection.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


@dataclass
class AlertRule:
    rule_id: str
    name: str
    metric_name: str
    condition: str          # gt, lt, gte, lte, eq, change_pct
    threshold: float
    window_seconds: int     # evaluation window
    action: str             # notify | auto_fix | escalate
    enabled: bool = True
    confidence_min: float = 0.85
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "window_seconds": self.window_seconds,
            "action": self.action,
            "enabled": self.enabled,
            "confidence_min": self.confidence_min,
            "created_at": self.created_at,
        }


@dataclass
class AlertEvent:
    alert_id: str
    rule_id: str
    metric_name: str
    current_value: float
    threshold: float
    severity: str           # info | warning | critical
    root_cause: str | None = None
    impact_estimate: str | None = None
    action_taken: str | None = None
    confidence: float = 0.0
    timestamp: float = 0.0
    resolved: bool = False

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "severity": self.severity,
            "root_cause": self.root_cause,
            "impact_estimate": self.impact_estimate,
            "action_taken": self.action_taken,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
        }


class CausalAlertEngine:
    """Monitors business metrics and generates causal alerts."""

    def __init__(self) -> None:
        db_path = config.get("alerts", "db_path") or "data/alerts.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id         TEXT PRIMARY KEY,
                    name            TEXT NOT NULL,
                    metric_name     TEXT NOT NULL,
                    condition       TEXT NOT NULL,
                    threshold       REAL NOT NULL,
                    window_seconds  INTEGER NOT NULL DEFAULT 300,
                    action          TEXT NOT NULL DEFAULT 'notify',
                    enabled         INTEGER NOT NULL DEFAULT 1,
                    confidence_min  REAL NOT NULL DEFAULT 0.85,
                    created_at      REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS metric_samples (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value       REAL NOT NULL,
                    timestamp   REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_ms_name ON metric_samples(metric_name);
                CREATE INDEX IF NOT EXISTS idx_ms_ts ON metric_samples(timestamp);

                CREATE TABLE IF NOT EXISTS alert_events (
                    alert_id        TEXT PRIMARY KEY,
                    rule_id         TEXT NOT NULL,
                    metric_name     TEXT NOT NULL,
                    current_value   REAL NOT NULL,
                    threshold       REAL NOT NULL,
                    severity        TEXT NOT NULL DEFAULT 'warning',
                    root_cause      TEXT,
                    impact_estimate TEXT,
                    action_taken    TEXT,
                    confidence      REAL NOT NULL DEFAULT 0,
                    timestamp       REAL NOT NULL,
                    resolved        INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_ae_ts ON alert_events(timestamp);
            """)
            conn.commit()

    # ── Metric recording ─────────────────────────────────────────────

    def record_metric(self, metric_name: str, value: float) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO metric_samples (metric_name, value, timestamp) VALUES (?, ?, ?)",
                (metric_name, value, time.time()),
            )
            conn.commit()

    def get_metric_history(
        self, metric_name: str, window_seconds: int = 3600, limit: int = 100,
    ) -> list[dict]:
        cutoff = time.time() - window_seconds
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT value, timestamp FROM metric_samples
                WHERE metric_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC LIMIT ?""",
                (metric_name, cutoff, limit),
            ).fetchall()
        return [{"value": r["value"], "timestamp": r["timestamp"]} for r in rows]

    # ── Rule CRUD ────────────────────────────────────────────────────

    def create_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,
        threshold: float,
        window_seconds: int = 300,
        action: str = "notify",
        confidence_min: float = 0.85,
    ) -> AlertRule:
        rule_id = str(uuid.uuid4())[:10]
        now = time.time()
        rule = AlertRule(
            rule_id=rule_id, name=name, metric_name=metric_name,
            condition=condition, threshold=threshold,
            window_seconds=window_seconds, action=action,
            confidence_min=confidence_min, created_at=now,
        )
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO alert_rules
                (rule_id, name, metric_name, condition, threshold, window_seconds,
                 action, enabled, confidence_min, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (rule_id, name, metric_name, condition, threshold,
                 window_seconds, action, confidence_min, now),
            )
            conn.commit()
        return rule

    def list_rules(self) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM alert_rules ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_rule(self, rule_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("DELETE FROM alert_rules WHERE rule_id = ?", (rule_id,)).rowcount
            conn.commit()
            return c > 0

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "UPDATE alert_rules SET enabled = ? WHERE rule_id = ?",
                (int(enabled), rule_id),
            ).rowcount
            conn.commit()
            return c > 0

    # ── Evaluation ───────────────────────────────────────────────────

    def evaluate_rules(self) -> list[AlertEvent]:
        """Evaluate all enabled rules against recent metric data."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rules = conn.execute("SELECT * FROM alert_rules WHERE enabled = 1").fetchall()

        triggered: list[AlertEvent] = []
        for rule in rules:
            samples = self.get_metric_history(rule["metric_name"], rule["window_seconds"])
            if not samples:
                continue

            avg_val = sum(s["value"] for s in samples) / len(samples)
            fired = self._check_condition(rule["condition"], avg_val, rule["threshold"])

            if fired:
                severity = "critical" if abs(avg_val - rule["threshold"]) > rule["threshold"] * 0.5 else "warning"
                alert = AlertEvent(
                    alert_id=str(uuid.uuid4())[:10],
                    rule_id=rule["rule_id"],
                    metric_name=rule["metric_name"],
                    current_value=round(avg_val, 4),
                    threshold=rule["threshold"],
                    severity=severity,
                    confidence=min(1.0, len(samples) / 10.0),
                    timestamp=time.time(),
                )
                self._save_alert(alert)
                triggered.append(alert)

        return triggered

    def _check_condition(self, condition: str, value: float, threshold: float) -> bool:
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return abs(value - threshold) < 0.001
        return False

    # ── Alert events query ───────────────────────────────────────────

    def get_alerts(self, resolved: bool | None = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM alert_events"
        params: list[Any] = []
        if resolved is not None:
            query += " WHERE resolved = ?"
            params.append(int(resolved))
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def resolve_alert(self, alert_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "UPDATE alert_events SET resolved = 1 WHERE alert_id = ?",
                (alert_id,),
            ).rowcount
            conn.commit()
            return c > 0

    def _save_alert(self, alert: AlertEvent) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO alert_events
                (alert_id, rule_id, metric_name, current_value, threshold,
                 severity, root_cause, impact_estimate, action_taken,
                 confidence, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (alert.alert_id, alert.rule_id, alert.metric_name,
                 alert.current_value, alert.threshold, alert.severity,
                 alert.root_cause, alert.impact_estimate, alert.action_taken,
                 alert.confidence, alert.timestamp),
            )
            conn.commit()

    def cleanup_old(self, days: int = 30) -> int:
        cutoff = time.time() - (days * 86400)
        with sqlite3.connect(str(self._db_path)) as conn:
            c1 = conn.execute("DELETE FROM metric_samples WHERE timestamp < ?", (cutoff,)).rowcount
            c2 = conn.execute("DELETE FROM alert_events WHERE timestamp < ? AND resolved = 1", (cutoff,)).rowcount
            conn.commit()
        return c1 + c2


# ── Singleton ────────────────────────────────────────────────────────────

_engine: CausalAlertEngine | None = None


def get_alert_engine() -> CausalAlertEngine:
    global _engine
    if _engine is None:
        _engine = CausalAlertEngine()
    return _engine
