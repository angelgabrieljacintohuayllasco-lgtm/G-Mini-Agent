"""
Security Audit Logger.

Comprehensive logging of critical actions with timestamp, actor, result.
Supports JSON/CSV export and configurable retention.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


class AuditCategory(str, Enum):
    AUTH = "auth"
    ACTION = "action"
    POLICY = "policy"
    RBAC = "rbac"
    ETHICAL = "ethical"
    INJECTION = "injection"
    SANDBOX = "sandbox"
    GATEWAY = "gateway"
    NODE = "node"
    CONFIG = "config"
    SKILL = "skill"
    PAYMENT = "payment"
    SYSTEM = "system"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class AuditEntry:
    event_id: str
    timestamp: float
    category: str
    severity: str
    actor: str           # user_id or system component
    action: str          # what happened
    target: str          # what was affected
    result: str          # "success", "blocked", "failed", "approved", "denied"
    details: dict[str, Any]
    session_id: str = ""
    ip_address: str = ""


class AuditLogger:
    """Persistent audit log for security-critical events."""

    def __init__(self) -> None:
        db_path = config.get("security", "audit", "db_path") or "data/audit.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._retention_days = config.get("security", "audit", "retention_days") or 90
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    event_id    TEXT PRIMARY KEY,
                    timestamp   REAL NOT NULL,
                    category    TEXT NOT NULL,
                    severity    TEXT NOT NULL,
                    actor       TEXT NOT NULL,
                    action      TEXT NOT NULL,
                    target      TEXT NOT NULL DEFAULT '',
                    result      TEXT NOT NULL,
                    details     TEXT NOT NULL DEFAULT '{}',
                    session_id  TEXT NOT NULL DEFAULT '',
                    ip_address  TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_log(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor)"
            )
            conn.commit()

    # ── Logging ──────────────────────────────────────────────────────

    def log(
        self,
        category: str,
        severity: str,
        actor: str,
        action: str,
        result: str,
        target: str = "",
        details: dict[str, Any] | None = None,
        session_id: str = "",
        ip_address: str = "",
    ) -> str:
        """Log an audit event. Returns event_id."""
        event_id = str(uuid.uuid4())
        timestamp = time.time()
        details_json = json.dumps(details or {}, default=str)

        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    """INSERT INTO audit_log
                    (event_id, timestamp, category, severity, actor, action, target, result, details, session_id, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, timestamp, category, severity, actor, action, target, result, details_json, session_id, ip_address),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")
            return ""

        # Also log to loguru for immediate visibility
        log_msg = f"AUDIT [{category}/{severity}] {actor}: {action} → {result}"
        if severity in (AuditSeverity.CRITICAL.value, AuditSeverity.BLOCKED.value):
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return event_id

    # Convenience methods
    def log_action(self, actor: str, action: str, result: str, **kwargs: Any) -> str:
        return self.log(AuditCategory.ACTION.value, AuditSeverity.INFO.value, actor, action, result, **kwargs)

    def log_blocked(self, actor: str, action: str, reason: str, **kwargs: Any) -> str:
        return self.log(
            AuditCategory.POLICY.value, AuditSeverity.BLOCKED.value,
            actor, action, "blocked", details={"reason": reason}, **kwargs,
        )

    def log_ethical_violation(self, actor: str, rule_id: str, description: str, **kwargs: Any) -> str:
        return self.log(
            AuditCategory.ETHICAL.value, AuditSeverity.CRITICAL.value,
            actor, f"ethical_violation:{rule_id}", "blocked",
            details={"description": description}, **kwargs,
        )

    def log_injection(self, source: str, confidence: float, patterns: list[str], **kwargs: Any) -> str:
        return self.log(
            AuditCategory.INJECTION.value, AuditSeverity.CRITICAL.value,
            source, "prompt_injection_detected", "blocked",
            details={"confidence": confidence, "patterns": patterns}, **kwargs,
        )

    def log_rbac(self, actor: str, action: str, result: str, **kwargs: Any) -> str:
        return self.log(AuditCategory.RBAC.value, AuditSeverity.INFO.value, actor, action, result, **kwargs)

    def log_payment(self, actor: str, action: str, amount_usd: float, result: str, **kwargs: Any) -> str:
        return self.log(
            AuditCategory.PAYMENT.value, AuditSeverity.WARNING.value,
            actor, action, result, details={"amount_usd": amount_usd}, **kwargs,
        )

    # ── Query ────────────────────────────────────────────────────────

    def query(
        self,
        category: str | None = None,
        severity: str | None = None,
        actor: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Query audit log with filters."""
        clauses = []
        params: list[Any] = []

        if category:
            clauses.append("category = ?")
            params.append(category)
        if severity:
            clauses.append("severity = ?")
            params.append(severity)
        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if until:
            clauses.append("timestamp <= ?")
            params.append(until)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            result = []
            for row in rows:
                entry = dict(row)
                entry["details"] = json.loads(entry.get("details", "{}"))
                result.append(entry)
            return result

    def count(
        self,
        category: str | None = None,
        severity: str | None = None,
        since: float | None = None,
    ) -> int:
        clauses = []
        params: list[Any] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if severity:
            clauses.append("severity = ?")
            params.append(severity)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM audit_log {where}", params).fetchone()
            return row[0] if row else 0

    def get_stats(self, hours: int = 24) -> dict:
        """Get audit statistics for the last N hours."""
        since = time.time() - (hours * 3600)
        with sqlite3.connect(str(self._db_path)) as conn:
            # By category
            rows = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM audit_log WHERE timestamp >= ? GROUP BY category",
                (since,),
            ).fetchall()
            by_category = {r[0]: r[1] for r in rows}

            # By severity
            rows = conn.execute(
                "SELECT severity, COUNT(*) as cnt FROM audit_log WHERE timestamp >= ? GROUP BY severity",
                (since,),
            ).fetchall()
            by_severity = {r[0]: r[1] for r in rows}

            # Total
            row = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?", (since,)
            ).fetchone()
            total = row[0] if row else 0

        return {
            "period_hours": hours,
            "total_events": total,
            "by_category": by_category,
            "by_severity": by_severity,
        }

    # ── Export ────────────────────────────────────────────────────────

    def export_json(self, **filters: Any) -> str:
        entries = self.query(limit=10000, **filters)
        return json.dumps(entries, indent=2, default=str)

    def export_csv(self, **filters: Any) -> str:
        entries = self.query(limit=10000, **filters)
        if not entries:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["event_id", "timestamp", "category", "severity", "actor", "action", "target", "result", "session_id"],
        )
        writer.writeheader()
        for entry in entries:
            row = {k: entry.get(k, "") for k in writer.fieldnames}
            writer.writerow(row)
        return output.getvalue()

    # ── Maintenance ──────────────────────────────────────────────────

    def cleanup_old(self) -> int:
        """Remove entries older than retention period."""
        cutoff = time.time() - (self._retention_days * 86400)
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            conn.commit()
            deleted = cur.rowcount
        if deleted:
            logger.info(f"Audit cleanup: removed {deleted} entries older than {self._retention_days}d")
        return deleted


# ── Singleton ────────────────────────────────────────────────────────────

_audit: AuditLogger | None = None


def get_audit() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit
