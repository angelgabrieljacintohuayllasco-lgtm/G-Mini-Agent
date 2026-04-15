"""
RLHF Lite — Lightweight reinforcement learning from human feedback.

Captures implicit/explicit signals, builds preference profiles,
and injects learned preferences into the system prompt.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


# Signal weights
IMPLICIT_SIGNALS = {
    "copy_no_edit": 0.6,
    "rewrite_request": -0.5,
    "long_session": 0.3,
    "immediate_followup": 0.2,
}

EXPLICIT_SIGNALS = {
    "thumbs_up": 0.9,
    "perfect": 1.0,
    "regenerate": -0.8,
    "undo_action": -1.0,
    "thumbs_down": -0.9,
    "good": 0.7,
    "bad": -0.7,
}


class RLHFLite:
    """Lightweight preference learning from user feedback signals."""

    PROFILE_STABLE_THRESHOLD = 847  # signals needed for stable profile

    def __init__(self) -> None:
        db_path = config.get("rlhf", "db_path") or "data/rlhf.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS feedback_signals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL DEFAULT 'default',
                    signal_type TEXT NOT NULL,
                    signal_name TEXT NOT NULL,
                    weight      REAL NOT NULL,
                    context     TEXT NOT NULL DEFAULT '{}',
                    timestamp   REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_fs_user ON feedback_signals(user_id);
                CREATE INDEX IF NOT EXISTS idx_fs_ts ON feedback_signals(timestamp);

                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id     TEXT NOT NULL,
                    pref_key    TEXT NOT NULL,
                    pref_value  REAL NOT NULL DEFAULT 0,
                    sample_count INTEGER NOT NULL DEFAULT 0,
                    updated_at  REAL NOT NULL,
                    PRIMARY KEY (user_id, pref_key)
                );
            """)
            conn.commit()

    # ── Signal recording ─────────────────────────────────────────────

    def record_signal(
        self,
        signal_name: str,
        user_id: str = "default",
        context: dict | None = None,
    ) -> dict:
        """Record a feedback signal (implicit or explicit)."""
        # Determine weight
        if signal_name in EXPLICIT_SIGNALS:
            weight = EXPLICIT_SIGNALS[signal_name]
            signal_type = "explicit"
        elif signal_name in IMPLICIT_SIGNALS:
            weight = IMPLICIT_SIGNALS[signal_name]
            signal_type = "implicit"
        else:
            weight = 0.0
            signal_type = "custom"

        ctx = context or {}
        now = time.time()

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO feedback_signals
                (user_id, signal_type, signal_name, weight, context, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, signal_type, signal_name, weight,
                 json.dumps(ctx), now),
            )
            conn.commit()

        # Update preferences based on context
        self._update_preferences(user_id, signal_name, weight, ctx)

        return {"signal_name": signal_name, "weight": weight, "type": signal_type}

    def _update_preferences(
        self, user_id: str, signal_name: str, weight: float, context: dict,
    ) -> None:
        """Extract preference signals from context and save."""
        prefs_to_update: dict[str, float] = {}

        # Extract preference dimensions from context
        if "response_length" in context:
            length = context["response_length"]
            if length == "short":
                prefs_to_update["concise_responses"] = weight
            elif length == "long":
                prefs_to_update["detailed_responses"] = weight

        if "code_included" in context:
            prefs_to_update["show_code"] = weight if context["code_included"] else -weight

        if "language" in context:
            prefs_to_update[f"lang_{context['language']}"] = abs(weight)

        if "task_type" in context:
            prefs_to_update[f"task_{context['task_type']}"] = weight

        # General satisfaction signal
        prefs_to_update["overall_satisfaction"] = weight

        # Update in DB with running average
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            for key, val in prefs_to_update.items():
                row = conn.execute(
                    "SELECT pref_value, sample_count FROM user_preferences WHERE user_id = ? AND pref_key = ?",
                    (user_id, key),
                ).fetchone()
                if row:
                    old_val, count = row
                    new_count = count + 1
                    # Exponential moving average
                    alpha = 2.0 / (new_count + 1)
                    new_val = old_val * (1 - alpha) + val * alpha
                    conn.execute(
                        "UPDATE user_preferences SET pref_value = ?, sample_count = ?, updated_at = ? WHERE user_id = ? AND pref_key = ?",
                        (new_val, new_count, now, user_id, key),
                    )
                else:
                    conn.execute(
                        "INSERT INTO user_preferences (user_id, pref_key, pref_value, sample_count, updated_at) VALUES (?, ?, ?, 1, ?)",
                        (user_id, key, val, now),
                    )
            conn.commit()

    # ── Preference queries ───────────────────────────────────────────

    def get_preferences(self, user_id: str = "default") -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ? ORDER BY sample_count DESC",
                (user_id,),
            ).fetchall()
        return [
            {
                "pref_key": r["pref_key"],
                "pref_value": round(r["pref_value"], 3),
                "sample_count": r["sample_count"],
                "confidence_pct": round(min(100, r["sample_count"] / self.PROFILE_STABLE_THRESHOLD * 100), 1),
            }
            for r in rows
        ]

    def delete_preference(self, user_id: str, pref_key: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "DELETE FROM user_preferences WHERE user_id = ? AND pref_key = ?",
                (user_id, pref_key),
            ).rowcount
            conn.commit()
            return c > 0

    def get_profile_summary(self, user_id: str = "default") -> dict:
        """Generate a human-readable preference summary."""
        prefs = self.get_preferences(user_id)
        total_signals = self._count_signals(user_id)
        is_stable = total_signals >= self.PROFILE_STABLE_THRESHOLD

        summary_parts = []
        for p in prefs:
            if p["sample_count"] >= 5:  # Only show pref with enough data
                val = p["pref_value"]
                pct = abs(round(val * 100))
                if val > 0.3:
                    summary_parts.append(f"{p['pref_key'].replace('_', ' ')}: prefiere ({pct}%)")
                elif val < -0.3:
                    summary_parts.append(f"{p['pref_key'].replace('_', ' ')}: evitar ({pct}%)")

        return {
            "user_id": user_id,
            "total_signals": total_signals,
            "is_stable": is_stable,
            "preferences_count": len(prefs),
            "summary": "; ".join(summary_parts) if summary_parts else "Aún no hay suficientes datos.",
            "preferences": prefs,
        }

    def get_context_injection(self, user_id: str = "default") -> str:
        """Generate a system prompt prefix from learned preferences."""
        prefs = self.get_preferences(user_id)
        if not prefs:
            return ""

        strong_prefs = [p for p in prefs if abs(p["pref_value"]) > 0.3 and p["sample_count"] >= 5]
        if not strong_prefs:
            return ""

        lines = ["[Preferencias aprendidas del usuario]"]
        for p in strong_prefs[:10]:  # cap at 10
            direction = "prefiere" if p["pref_value"] > 0 else "evita"
            key = p["pref_key"].replace("_", " ")
            lines.append(f"- {key}: {direction} (confianza: {p['confidence_pct']}%)")

        return "\n".join(lines)

    # ── Stats ────────────────────────────────────────────────────────

    def _count_signals(self, user_id: str) -> int:
        with sqlite3.connect(str(self._db_path)) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM feedback_signals WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

    def get_signal_history(self, user_id: str = "default", limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT signal_type, signal_name, weight, timestamp FROM feedback_signals WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]


# ── Singleton ────────────────────────────────────────────────────────────

_rlhf: RLHFLite | None = None


def get_rlhf() -> RLHFLite:
    global _rlhf
    if _rlhf is None:
        _rlhf = RLHFLite()
    return _rlhf
