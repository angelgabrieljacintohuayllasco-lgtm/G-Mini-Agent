"""
Productivity Suite — Clipboard, Notifications, File Manager,
Price Tracker, System Optimizer, etc.

Modular registry of productivity tools accessible via API.
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


# ═══════════════════════════════════════════════════════════════════════
# Smart Clipboard
# ═══════════════════════════════════════════════════════════════════════

class SmartClipboard:
    """Multi-clipboard with history and search."""

    def __init__(self) -> None:
        db_path = config.get("productivity", "db_path") or "data/productivity.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clipboard_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    content     TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'text',
                    source      TEXT NOT NULL DEFAULT '',
                    pinned      INTEGER NOT NULL DEFAULT 0,
                    timestamp   REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clip_ts ON clipboard_history(timestamp)")
            conn.commit()

    def add(self, content: str, content_type: str = "text", source: str = "") -> dict:
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                "INSERT INTO clipboard_history (content, content_type, source, timestamp) VALUES (?, ?, ?, ?)",
                (content, content_type, source, now),
            )
            conn.commit()
            return {"id": cur.lastrowid, "timestamp": now}

    def get_history(self, limit: int = 50, search: str | None = None) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if search:
                rows = conn.execute(
                    "SELECT * FROM clipboard_history WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                    (f"%{search}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM clipboard_history ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def pin(self, clip_id: int, pinned: bool = True) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "UPDATE clipboard_history SET pinned = ? WHERE id = ?",
                (int(pinned), clip_id),
            ).rowcount
            conn.commit()
            return c > 0

    def delete(self, clip_id: int) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("DELETE FROM clipboard_history WHERE id = ?", (clip_id,)).rowcount
            conn.commit()
            return c > 0

    def clear_unpinned(self) -> int:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("DELETE FROM clipboard_history WHERE pinned = 0").rowcount
            conn.commit()
            return c


# ═══════════════════════════════════════════════════════════════════════
# Smart Notifications
# ═══════════════════════════════════════════════════════════════════════

class NotificationManager:
    """Smart notification system with prioritization and suppression."""

    def __init__(self) -> None:
        db_path = config.get("productivity", "db_path") or "data/productivity.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._suppressed = False
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT NOT NULL,
                    body        TEXT NOT NULL DEFAULT '',
                    channel     TEXT NOT NULL DEFAULT 'system',
                    priority    INTEGER NOT NULL DEFAULT 5,
                    read        INTEGER NOT NULL DEFAULT 0,
                    acted       INTEGER NOT NULL DEFAULT 0,
                    action_url  TEXT,
                    timestamp   REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_ts ON notifications(timestamp)")
            conn.commit()

    def send(
        self,
        title: str,
        body: str = "",
        channel: str = "system",
        priority: int = 5,
        action_url: str | None = None,
    ) -> dict:
        if self._suppressed and priority < 9:
            return {"suppressed": True}
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                """INSERT INTO notifications (title, body, channel, priority, action_url, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (title, body, channel, priority, action_url, now),
            )
            conn.commit()
            return {"id": cur.lastrowid, "timestamp": now}

    def get_notifications(
        self, unread_only: bool = False, channel: str | None = None, limit: int = 50,
    ) -> list[dict]:
        query = "SELECT * FROM notifications"
        params: list[Any] = []
        conditions = []
        if unread_only:
            conditions.append("read = 0")
        if channel:
            conditions.append("channel = ?")
            params.append(channel)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY priority DESC, timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def mark_read(self, notif_id: int) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notif_id,)).rowcount
            conn.commit()
            return c > 0

    def mark_all_read(self) -> int:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("UPDATE notifications SET read = 1 WHERE read = 0").rowcount
            conn.commit()
            return c

    def suppress(self, enabled: bool = True) -> None:
        self._suppressed = enabled

    def get_summary(self) -> dict:
        with sqlite3.connect(str(self._db_path)) as conn:
            unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE read = 0").fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        return {"unread": unread, "total": total, "suppressed": self._suppressed}


# ═══════════════════════════════════════════════════════════════════════
# Price Tracker
# ═══════════════════════════════════════════════════════════════════════

class PriceTracker:
    """Monitor prices across stores with alert thresholds."""

    def __init__(self) -> None:
        db_path = config.get("productivity", "db_path") or "data/productivity.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tracked_products (
                    product_id  TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    url         TEXT NOT NULL,
                    store       TEXT NOT NULL DEFAULT '',
                    target_price REAL,
                    created_at  REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id  TEXT NOT NULL,
                    price       REAL NOT NULL,
                    currency    TEXT NOT NULL DEFAULT 'USD',
                    timestamp   REAL NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES tracked_products(product_id)
                );

                CREATE INDEX IF NOT EXISTS idx_ph_prod ON price_history(product_id);
            """)
            conn.commit()

    def add_product(
        self, name: str, url: str, store: str = "", target_price: float | None = None,
    ) -> dict:
        product_id = str(uuid.uuid4())[:10]
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO tracked_products (product_id, name, url, store, target_price, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, name, url, store, target_price, now),
            )
            conn.commit()
        return {"product_id": product_id, "name": name}

    def record_price(self, product_id: str, price: float, currency: str = "USD") -> dict:
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO price_history (product_id, price, currency, timestamp) VALUES (?, ?, ?, ?)",
                (product_id, price, currency, now),
            )
            conn.commit()
        return {"product_id": product_id, "price": price, "timestamp": now}

    def list_products(self) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM tracked_products ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get_price_history(self, product_id: str, limit: int = 100) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT price, currency, timestamp FROM price_history WHERE product_id = ? ORDER BY timestamp DESC LIMIT ?",
                (product_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def check_alerts(self) -> list[dict]:
        """Check which products have reached target price."""
        alerts = []
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            products = conn.execute(
                "SELECT * FROM tracked_products WHERE target_price IS NOT NULL"
            ).fetchall()
            for p in products:
                latest = conn.execute(
                    "SELECT price FROM price_history WHERE product_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (p["product_id"],),
                ).fetchone()
                if latest and latest["price"] <= p["target_price"]:
                    alerts.append({
                        "product_id": p["product_id"],
                        "name": p["name"],
                        "current_price": latest["price"],
                        "target_price": p["target_price"],
                    })
        return alerts

    def delete_product(self, product_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
            c = conn.execute("DELETE FROM tracked_products WHERE product_id = ?", (product_id,)).rowcount
            conn.commit()
            return c > 0


# ═══════════════════════════════════════════════════════════════════════
# System Optimizer
# ═══════════════════════════════════════════════════════════════════════

class SystemOptimizer:
    """System health monitoring and optimization recommendations."""

    def get_system_info(self) -> dict:
        import os
        import platform
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "cwd": os.getcwd(),
        }

    def get_disk_usage(self, path: str = ".") -> dict:
        import shutil
        try:
            usage = shutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "used_pct": round(usage.used / usage.total * 100, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def find_large_files(self, path: str = ".", min_mb: int = 100, limit: int = 20) -> list[dict]:
        import os
        large_files = []
        min_bytes = min_mb * 1024 * 1024
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                        if size >= min_bytes:
                            large_files.append({
                                "path": fp,
                                "size_mb": round(size / (1024**2), 1),
                            })
                    except OSError:
                        continue
        except OSError:
            pass
        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        return large_files[:limit]


# ═══════════════════════════════════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════════════════════════════════

_clipboard: SmartClipboard | None = None
_notifications: NotificationManager | None = None
_price_tracker: PriceTracker | None = None
_optimizer: SystemOptimizer | None = None


def get_clipboard() -> SmartClipboard:
    global _clipboard
    if _clipboard is None:
        _clipboard = SmartClipboard()
    return _clipboard


def get_notifications() -> NotificationManager:
    global _notifications
    if _notifications is None:
        _notifications = NotificationManager()
    return _notifications


def get_price_tracker() -> PriceTracker:
    global _price_tracker
    if _price_tracker is None:
        _price_tracker = PriceTracker()
    return _price_tracker


def get_system_optimizer() -> SystemOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = SystemOptimizer()
    return _optimizer
