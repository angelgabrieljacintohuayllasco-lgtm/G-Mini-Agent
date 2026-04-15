"""
Event Bus — Central pub/sub system with persistent queue.

Unifies: gateway, cron, webhooks, nodes, skills, core.
Event contract: event_id, type, source, timestamp, payload, session_id.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger

from backend.config import config


@dataclass
class Event:
    event_id: str
    event_type: str
    source: str
    payload: dict[str, Any]
    session_id: str = ""
    timestamp: float = 0.0
    processed: bool = False

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "processed": self.processed,
        }


class EventBus:
    """Central event bus with pub/sub and persistent queue."""

    def __init__(self) -> None:
        db_path = config.get("event_bus", "db_path") or "data/event_bus.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._wildcard_subscribers: list[Callable] = []
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id    TEXT PRIMARY KEY,
                    event_type  TEXT NOT NULL,
                    source      TEXT NOT NULL DEFAULT '',
                    payload     TEXT NOT NULL DEFAULT '{}',
                    session_id  TEXT NOT NULL DEFAULT '',
                    timestamp   REAL NOT NULL,
                    processed   INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_proc ON events(processed)")
            conn.commit()

    # ── Pub/Sub ──────────────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe a handler to a specific event type."""
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        """Subscribe a handler to ALL event types."""
        self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h is not handler
            ]

    # ── Publishing ───────────────────────────────────────────────────

    async def emit(
        self,
        event_type: str,
        payload: dict | None = None,
        source: str = "",
        session_id: str = "",
    ) -> Event:
        """Emit an event: persist to queue and notify subscribers."""
        event = Event(
            event_id=str(uuid.uuid4())[:12],
            event_type=event_type,
            source=source,
            payload=payload or {},
            session_id=session_id,
            timestamp=time.time(),
        )

        # Persist to queue
        self._persist_event(event)

        # Notify subscribers
        await self._dispatch(event)

        return event

    def emit_sync(
        self,
        event_type: str,
        payload: dict | None = None,
        source: str = "",
        session_id: str = "",
    ) -> Event:
        """Synchronous emit for non-async contexts."""
        event = Event(
            event_id=str(uuid.uuid4())[:12],
            event_type=event_type,
            source=source,
            payload=payload or {},
            session_id=session_id,
            timestamp=time.time(),
        )
        self._persist_event(event)
        return event

    async def _dispatch(self, event: Event) -> None:
        handlers = list(self._subscribers.get(event.event_type, []))
        handlers.extend(self._wildcard_subscribers)

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")

        # Mark as processed
        self._mark_processed(event.event_id)

    # ── Persistent queue ─────────────────────────────────────────────

    def _persist_event(self, event: Event) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO events
                (event_id, event_type, source, payload, session_id, timestamp, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event.event_id, event.event_type, event.source,
                 json.dumps(event.payload), event.session_id,
                 event.timestamp, 0),
            )
            conn.commit()

    def _mark_processed(self, event_id: str) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("UPDATE events SET processed = 1 WHERE event_id = ?", (event_id,))
            conn.commit()

    async def process_pending(self) -> int:
        """Process events that survived a restart (unprocessed)."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events WHERE processed = 0 ORDER BY timestamp ASC LIMIT 100"
            ).fetchall()

        count = 0
        for row in rows:
            event = Event(
                event_id=row["event_id"],
                event_type=row["event_type"],
                source=row["source"],
                payload=json.loads(row["payload"]),
                session_id=row["session_id"],
                timestamp=row["timestamp"],
            )
            await self._dispatch(event)
            count += 1

        return count

    # ── Query ────────────────────────────────────────────────────────

    def get_events(
        self,
        event_type: str | None = None,
        source: str | None = None,
        since: float | None = None,
        limit: int = 50,
    ) -> list[dict]:
        query = "SELECT * FROM events"
        params: list[Any] = []
        conditions = []
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "source": r["source"],
                "payload": json.loads(r["payload"]),
                "session_id": r["session_id"],
                "timestamp": r["timestamp"],
                "processed": bool(r["processed"]),
            }
            for r in rows
        ]

    def get_stats(self) -> dict:
        with sqlite3.connect(str(self._db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM events WHERE processed = 0").fetchone()[0]
            conn.row_factory = sqlite3.Row
            by_type = conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM events GROUP BY event_type ORDER BY cnt DESC LIMIT 20"
            ).fetchall()
        return {
            "total_events": total,
            "pending": pending,
            "by_type": [{"type": r["event_type"], "count": r["cnt"]} for r in by_type],
        }

    def cleanup_old(self, days: int = 30) -> int:
        cutoff = time.time() - (days * 86400)
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("DELETE FROM events WHERE timestamp < ? AND processed = 1", (cutoff,)).rowcount
            conn.commit()
        return c


# ── Singleton ────────────────────────────────────────────────────────────

_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
