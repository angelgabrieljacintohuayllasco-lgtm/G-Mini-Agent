"""
Session Compression Engine.

Automatically compresses long conversations when approaching context limits.
Generates structured task maps and resumable session summaries.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


@dataclass
class SessionSummary:
    session_id: str
    original_message_count: int
    compressed_at: float
    objective: str
    key_facts: list[str]
    decisions: list[str]
    pending_tasks: list[str]
    summary_text: str
    context_tokens_before: int
    context_tokens_after: int


@dataclass
class TaskMapEntry:
    task_id: str
    description: str
    status: str  # "completed", "in_progress", "pending", "blocked"
    dependencies: list[str] = field(default_factory=list)
    result: str = ""


class SessionCompressor:
    """Compresses conversation history to preserve context within token limits."""

    def __init__(self) -> None:
        db_path = config.get("memory", "compression_db_path") or "data/memory_ltm.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_threshold = config.get("memory", "compression_trigger_tokens") or 80000
        self._target_tokens = config.get("memory", "compression_target_tokens") or 20000
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id   TEXT PRIMARY KEY,
                    summary_json TEXT NOT NULL,
                    task_map     TEXT NOT NULL DEFAULT '[]',
                    compressed_at REAL NOT NULL,
                    original_count INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    @staticmethod
    def estimate_tokens(messages: list[dict]) -> int:
        """Rough token estimate: ~4 chars per token."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def should_compress(self, messages: list[dict]) -> bool:
        """Check if current conversation exceeds compression threshold."""
        return self.estimate_tokens(messages) >= self._token_threshold

    def compress(
        self,
        session_id: str,
        messages: list[dict],
        objective: str = "",
    ) -> tuple[list[dict], SessionSummary]:
        """Compress conversation history, keeping recent messages and a structured summary.

        Returns (compressed_messages, summary).
        """
        tokens_before = self.estimate_tokens(messages)

        if tokens_before < self._token_threshold:
            summary = SessionSummary(
                session_id=session_id,
                original_message_count=len(messages),
                compressed_at=time.time(),
                objective=objective,
                key_facts=[],
                decisions=[],
                pending_tasks=[],
                summary_text="No compression needed",
                context_tokens_before=tokens_before,
                context_tokens_after=tokens_before,
            )
            return messages, summary

        # Strategy: keep system prompt + last N messages, summarize the rest
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        # Keep last 20 messages (recent context)
        keep_count = min(20, len(non_system))
        old_msgs = non_system[:-keep_count] if keep_count < len(non_system) else []
        recent_msgs = non_system[-keep_count:] if keep_count > 0 else non_system

        # Extract structured info from old messages
        key_facts = []
        decisions = []
        pending_tasks = []
        task_map: list[dict] = []

        for msg in old_msgs:
            content = msg.get("content", "")
            role = msg.get("role", "")

            # Extract facts from assistant responses
            if role == "assistant" and len(content) > 50:
                # Take first sentence as a fact
                first_line = content.split(".")[0].strip()
                if len(first_line) > 20 and len(first_line) < 200:
                    key_facts.append(first_line)

            # Extract user decisions/requests
            if role == "user" and len(content) > 10:
                if any(kw in content.lower() for kw in ["hacer", "crear", "cambiar", "eliminar", "do", "create", "update", "delete"]):
                    decisions.append(content[:150])

        # Limit extractions
        key_facts = key_facts[-15:]
        decisions = decisions[-10:]

        # Build summary text
        summary_parts = []
        if objective:
            summary_parts.append(f"Objetivo: {objective}")
        if key_facts:
            summary_parts.append("Hechos clave:\n" + "\n".join(f"- {f}" for f in key_facts[-8:]))
        if decisions:
            summary_parts.append("Decisiones tomadas:\n" + "\n".join(f"- {d}" for d in decisions[-5:]))

        summary_text = "\n\n".join(summary_parts) if summary_parts else "Sesión larga comprimida."

        # Build compressed message list
        compression_msg = {
            "role": "system",
            "content": f"[Contexto restaurado] {summary_text}\n\nContinuamos la conversación. ¿Seguimos?",
        }
        compressed = system_msgs + [compression_msg] + recent_msgs

        tokens_after = self.estimate_tokens(compressed)

        summary = SessionSummary(
            session_id=session_id,
            original_message_count=len(messages),
            compressed_at=time.time(),
            objective=objective,
            key_facts=key_facts,
            decisions=decisions,
            pending_tasks=pending_tasks,
            summary_text=summary_text,
            context_tokens_before=tokens_before,
            context_tokens_after=tokens_after,
        )

        # Persist summary
        self._save_summary(summary, task_map)

        logger.info(
            f"Session compressed: {tokens_before} → {tokens_after} tokens "
            f"({len(messages)} → {len(compressed)} messages)"
        )

        return compressed, summary

    def _save_summary(self, summary: SessionSummary, task_map: list[dict]) -> None:
        summary_json = json.dumps({
            "objective": summary.objective,
            "key_facts": summary.key_facts,
            "decisions": summary.decisions,
            "pending_tasks": summary.pending_tasks,
            "summary_text": summary.summary_text,
            "original_count": summary.original_message_count,
            "tokens_before": summary.context_tokens_before,
            "tokens_after": summary.context_tokens_after,
        })
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO session_summaries (session_id, summary_json, task_map, compressed_at, original_count) VALUES (?, ?, ?, ?, ?)",
                (summary.session_id, summary_json, json.dumps(task_map), summary.compressed_at, summary.original_message_count),
            )
            conn.commit()

    def get_summary(self, session_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM session_summaries WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "session_id": row["session_id"],
                "summary": json.loads(row["summary_json"]),
                "task_map": json.loads(row["task_map"]),
                "compressed_at": row["compressed_at"],
                "original_count": row["original_count"],
            }

    def restore_context(self, session_id: str) -> str | None:
        """Generate a restoration message for resuming a previous session."""
        data = self.get_summary(session_id)
        if not data:
            return None
        summary = data["summary"]
        parts = [f"[Contexto restaurado de sesión anterior]"]
        if summary.get("objective"):
            parts.append(f"Objetivo: {summary['objective']}")
        if summary.get("key_facts"):
            parts.append("Hechos clave:")
            for f in summary["key_facts"][-5:]:
                parts.append(f"  - {f}")
        if summary.get("pending_tasks"):
            parts.append("Tareas pendientes:")
            for t in summary["pending_tasks"]:
                parts.append(f"  - {t}")
        parts.append("\n¿Seguimos donde lo dejamos?")
        return "\n".join(parts)


# ── Singleton ────────────────────────────────────────────────────────────

_compressor: SessionCompressor | None = None


def get_compressor() -> SessionCompressor:
    global _compressor
    if _compressor is None:
        _compressor = SessionCompressor()
    return _compressor
