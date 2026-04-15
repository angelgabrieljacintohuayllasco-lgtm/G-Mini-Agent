"""
G-Mini Agent - Gateway multi-canal (base operativa).
Mantiene sesiones conectadas, outbox persistente y entrega local a la app.
"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from loguru import logger

from backend.config import ROOT_DIR, config
from backend.core.gateway_discord import DISCORD_CHANNEL, DiscordGatewayConnector
from backend.core.gateway_telegram import TELEGRAM_CHANNEL, TelegramGatewayConnector
from backend.core.gateway_whatsapp import WHATSAPP_CHANNEL, WhatsAppGatewayConnector
from backend.core.gateway_slack import SLACK_CHANNEL, SlackGatewayConnector

DB_DIR = ROOT_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
DEFAULT_DB_PATH = DB_DIR / "gateway.db"
ARTIFACTS_DIR = DB_DIR / "gateway" / "artifacts"

LOCAL_APP_CHANNEL = "local_app"
LOCAL_APP_DEFAULT_SESSION = "main"
SUPPORTED_CHANNELS = ("local_app", "telegram", "whatsapp", "discord", "slack")
VIRTUAL_SID_PREFIX = "gw::"


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "si", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _resolve_gateway_db_path() -> Path:
    configured = str(config.get("gateway", "db_path", default=str(DEFAULT_DB_PATH)) or "").strip()
    if not configured:
        return DEFAULT_DB_PATH
    candidate = Path(configured)
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    return candidate


def _normalize_channel(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_session_key(value: Any, *, default: str = LOCAL_APP_DEFAULT_SESSION) -> str:
    normalized = str(value or "").strip().lower()
    return normalized or default


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    return []


class GatewayService:
    def __init__(self, db_path: Path | None = None):
        self._db_path = Path(db_path) if db_path else _resolve_gateway_db_path()
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._sio = None
        self._agent_core = None
        self._stream_buffers: dict[str, str] = {}
        self._discord = DiscordGatewayConnector(self)
        self._telegram = TelegramGatewayConnector(self)
        self._whatsapp = WhatsAppGatewayConnector(self)
        self._slack = SlackGatewayConnector(self)

    @property
    def enabled(self) -> bool:
        return _coerce_bool(config.get("gateway", "enabled", default=True), default=True)

    def attach_socket_server(self, sio) -> None:
        self._sio = sio

    def attach_agent_core(self, agent_core) -> None:
        self._agent_core = agent_core

    @property
    def agent_core(self):
        return self._agent_core

    def channel_enabled(self, channel: str) -> bool:
        return self._channel_enabled(channel)

    def _persist_artifact_bytes(self, data: bytes, filename: str) -> Path:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = Path(str(filename or "artifact.bin")).name or "artifact.bin"
        target = ARTIFACTS_DIR / f"{uuid.uuid4().hex[:12]}_{safe_name}"
        target.write_bytes(data)
        return target

    async def initialize(self) -> None:
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gateway_sessions (
                        sid TEXT PRIMARY KEY,
                        channel TEXT NOT NULL,
                        session_key TEXT NOT NULL,
                        display_name TEXT DEFAULT '',
                        connected INTEGER NOT NULL DEFAULT 1,
                        meta_json TEXT DEFAULT '{}',
                        connected_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL,
                        disconnected_at TEXT
                    )
                    """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gateway_outbox (
                        notification_id TEXT PRIMARY KEY,
                        channel TEXT NOT NULL,
                        session_key TEXT NOT NULL,
                        level TEXT NOT NULL DEFAULT 'info',
                        title TEXT NOT NULL,
                        body TEXT DEFAULT '',
                        payload_json TEXT DEFAULT '{}',
                        source_type TEXT DEFAULT '',
                        source_id TEXT DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'queued',
                        attempts INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT DEFAULT '',
                        created_at TEXT NOT NULL,
                        delivered_at TEXT
                    )
                    """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gateway_state (
                        state_key TEXT PRIMARY KEY,
                        value_json TEXT DEFAULT '{}',
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_gateway_sessions_channel ON gateway_sessions (channel, session_key, connected)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_gateway_outbox_channel ON gateway_outbox (channel, session_key, status, created_at DESC)"
                )
                await db.commit()
            self._initialized = True
            await self._sync_connectors()
            logger.info(f"GatewayService inicializado: {self._db_path}")

    async def shutdown(self) -> None:
        self._stream_buffers.clear()
        await self._discord.stop()
        await self._telegram.stop()
        await self._whatsapp.stop()
        await self._slack.stop()

    async def reload_config(self) -> None:
        await self.initialize()
        await self._sync_connectors()
        logger.info(f"GatewayService recargado: enabled={self.enabled}")

    def _channel_enabled(self, channel: str) -> bool:
        if not self.enabled:
            return False
        return _coerce_bool(
            config.get("gateway", "channels", channel, "enabled", default=(channel == LOCAL_APP_CHANNEL)),
            default=(channel == LOCAL_APP_CHANNEL),
        )

    async def _sync_connectors(self) -> None:
        if self._channel_enabled(DISCORD_CHANNEL) and (self._discord.bot_token or self._discord.fake_mode):
            await self._discord.start()
        else:
            await self._discord.stop()

        if self._channel_enabled(TELEGRAM_CHANNEL) and self._telegram.bot_token:
            await self._telegram.start()
        else:
            await self._telegram.stop()

        if self._channel_enabled(WHATSAPP_CHANNEL):
            await self._whatsapp.start()
        else:
            await self._whatsapp.stop()

        if self._channel_enabled(SLACK_CHANNEL) and (self._slack.bot_token and self._slack.app_token):
            await self._slack.start()
        else:
            await self._slack.stop()

    def _parse_target(self, target: str | None = None, *, default_channel: str = LOCAL_APP_CHANNEL) -> tuple[str, str]:
        raw_target = str(target or "").strip()
        if ":" in raw_target:
            channel, session_key = raw_target.split(":", 1)
            return _normalize_channel(channel), _normalize_session_key(session_key)
        return _normalize_channel(default_channel), _normalize_session_key(raw_target)

    def build_virtual_sid(self, channel: str, session_key: str) -> str:
        encoded = base64.urlsafe_b64encode(
            str(session_key or LOCAL_APP_DEFAULT_SESSION).encode("utf-8")
        ).decode("ascii").rstrip("=")
        return f"{VIRTUAL_SID_PREFIX}{_normalize_channel(channel)}::{encoded}"

    def parse_virtual_sid(self, sid: str) -> tuple[str, str] | None:
        raw = str(sid or "").strip()
        if not raw.startswith(VIRTUAL_SID_PREFIX):
            return None
        remainder = raw[len(VIRTUAL_SID_PREFIX):]
        if "::" not in remainder:
            return None
        channel, encoded = remainder.split("::", 1)
        padding = "=" * (-len(encoded) % 4)
        try:
            session_key = base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii")).decode("utf-8")
        except Exception:
            return None
        return _normalize_channel(channel), _normalize_session_key(session_key)

    def is_virtual_sid(self, sid: str) -> bool:
        return self.parse_virtual_sid(sid) is not None

    async def get_state_value(self, state_key: str, default: Any = None) -> Any:
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT value_json FROM gateway_state WHERE state_key = ?",
                (str(state_key or "").strip(),),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return default
        return self._safe_json_loads(row["value_json"], default)

    async def set_state_value(self, state_key: str, value: Any) -> None:
        await self.initialize()
        now_iso = _serialize_dt(_utcnow())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO gateway_state (state_key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    str(state_key or "").strip(),
                    json.dumps(value, ensure_ascii=False),
                    now_iso,
                ),
            )
            await db.commit()

    async def _upsert_session(
        self,
        sid: str,
        *,
        channel: str,
        session_key: str,
        display_name: str,
        connected: bool,
        meta: dict[str, Any] | None = None,
    ) -> None:
        await self.initialize()
        now_iso = _serialize_dt(_utcnow())
        disconnected_at = None if connected else now_iso
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO gateway_sessions (
                    sid, channel, session_key, display_name, connected,
                    meta_json, connected_at, last_seen_at, disconnected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sid) DO UPDATE SET
                    channel = excluded.channel,
                    session_key = excluded.session_key,
                    display_name = excluded.display_name,
                    connected = excluded.connected,
                    meta_json = excluded.meta_json,
                    connected_at = CASE
                        WHEN gateway_sessions.connected = 1 THEN gateway_sessions.connected_at
                        ELSE excluded.connected_at
                    END,
                    last_seen_at = excluded.last_seen_at,
                    disconnected_at = excluded.disconnected_at
                """,
                (
                    sid,
                    _normalize_channel(channel),
                    _normalize_session_key(session_key),
                    str(display_name or "").strip(),
                    1 if connected else 0,
                    json.dumps(meta or {}, ensure_ascii=False),
                    now_iso,
                    now_iso,
                    disconnected_at,
                ),
            )
            await db.commit()

    async def register_local_session(
        self,
        sid: str,
        *,
        session_key: str = LOCAL_APP_DEFAULT_SESSION,
        display_name: str = "G-Mini App",
        meta: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        await self._upsert_session(
            sid,
            channel=LOCAL_APP_CHANNEL,
            session_key=session_key,
            display_name=display_name or "G-Mini App",
            connected=True,
            meta=meta,
        )
        await self.deliver_pending(channel=LOCAL_APP_CHANNEL, session_key=session_key)

    async def register_remote_session(
        self,
        channel: str,
        *,
        session_key: str,
        display_name: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        await self._upsert_session(
            self.build_virtual_sid(channel, session_key),
            channel=channel,
            session_key=session_key,
            display_name=display_name,
            connected=True,
            meta=meta,
        )
        await self.deliver_pending(channel=channel, session_key=session_key)

    async def touch_local_session(self, sid: str) -> None:
        if not self._initialized:
            return
        now_iso = _serialize_dt(_utcnow())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE gateway_sessions
                SET last_seen_at = ?, connected = 1, disconnected_at = NULL
                WHERE sid = ?
                """,
                (now_iso, sid),
            )
            await db.commit()

    async def touch_remote_session(self, channel: str, session_key: str) -> None:
        await self.touch_local_session(self.build_virtual_sid(channel, session_key))

    async def unregister_local_session(self, sid: str) -> None:
        if not self._initialized:
            return
        now_iso = _serialize_dt(_utcnow())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE gateway_sessions
                SET connected = 0, disconnected_at = ?, last_seen_at = ?
                WHERE sid = ?
                """,
                (now_iso, now_iso, sid),
            )
            await db.commit()

    async def list_sessions(
        self,
        *,
        channel: str | None = None,
        connected_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        await self.initialize()
        clauses: list[str] = []
        params: list[Any] = []
        if channel:
            clauses.append("channel = ?")
            params.append(_normalize_channel(channel))
        if connected_only:
            clauses.append("connected = 1")
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = (
            "SELECT * FROM gateway_sessions"
            + where_clause
            + " ORDER BY connected DESC, last_seen_at DESC LIMIT ?"
        )
        params.append(max(1, min(int(limit), 500)))
        sessions: list[dict[str, Any]] = []
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, tuple(params)) as cursor:
                async for row in cursor:
                    sessions.append(self._row_to_session(dict(row)))
        return sessions

    async def list_outbox(
        self,
        *,
        channel: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        await self.initialize()
        clauses: list[str] = []
        params: list[Any] = []
        if channel:
            clauses.append("channel = ?")
            params.append(_normalize_channel(channel))
        if status:
            clauses.append("status = ?")
            params.append(str(status).strip().lower())
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = (
            "SELECT * FROM gateway_outbox"
            + where_clause
            + " ORDER BY created_at DESC LIMIT ?"
        )
        params.append(max(1, min(int(limit), 500)))
        items: list[dict[str, Any]] = []
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, tuple(params)) as cursor:
                async for row in cursor:
                    items.append(self._row_to_outbox(dict(row)))
        return items

    async def get_status(self) -> dict[str, Any]:
        await self.initialize()
        queued_notifications = 0
        delivered_notifications = 0
        failed_notifications = 0
        session_rows: list[dict[str, Any]] = []
        outbox_by_channel: dict[str, int] = {}
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT status, COUNT(*) AS total FROM gateway_outbox GROUP BY status"
            ) as cursor:
                async for row in cursor:
                    status = str(row["status"] or "")
                    total = int(row["total"] or 0)
                    if status == "queued":
                        queued_notifications = total
                    elif status == "delivered":
                        delivered_notifications = total
                    elif status == "failed":
                        failed_notifications = total
            async with db.execute(
                "SELECT channel, COUNT(*) AS total FROM gateway_outbox WHERE status = 'queued' GROUP BY channel"
            ) as cursor:
                async for row in cursor:
                    outbox_by_channel[str(row["channel"] or "")] = int(row["total"] or 0)
            async with db.execute(
                "SELECT channel, session_key, connected, COUNT(*) AS total FROM gateway_sessions GROUP BY channel, session_key, connected"
            ) as cursor:
                async for row in cursor:
                    session_rows.append(dict(row))

        connected_sessions = sum(
            int(row.get("total", 0))
            for row in session_rows
            if int(row.get("connected", 0)) == 1
        )

        channels: list[dict[str, Any]] = []
        for channel in SUPPORTED_CHANNELS:
            enabled = self._channel_enabled(channel)
            implemented = channel in {LOCAL_APP_CHANNEL, DISCORD_CHANNEL, TELEGRAM_CHANNEL, WHATSAPP_CHANNEL}
            connected_count = sum(
                int(row.get("total", 0))
                for row in session_rows
                if row.get("channel") == channel and int(row.get("connected", 0)) == 1
            )
            pending = int(outbox_by_channel.get(channel, 0))
            ready = False
            if channel == LOCAL_APP_CHANNEL:
                ready = enabled and self._sio is not None
                detail = (
                    "Entrega en vivo por Socket.IO a la app local."
                    if ready
                    else "Sin socket activo para entrega en vivo."
                )
            elif channel == DISCORD_CHANNEL:
                ready = enabled and self._discord.ready
                detail = self._discord.get_status_detail()
            elif channel == TELEGRAM_CHANNEL:
                ready = enabled and self._telegram.running and bool(self._telegram.bot_token)
                detail = self._telegram.get_status_detail()
            elif channel == WHATSAPP_CHANNEL:
                ready = enabled and self._whatsapp.ready
                detail = self._whatsapp.get_status_detail()
            else:
                detail = "Canal configurado pero con conector pendiente." if enabled else "Canal deshabilitado."
            channels.append(
                {
                    "channel": channel,
                    "enabled": enabled,
                    "implemented": implemented,
                    "ready": ready,
                    "connected_sessions": connected_count,
                    "queued_notifications": pending,
                    "detail": detail,
                }
            )

        return {
            "enabled": self.enabled,
            "default_channel": str(config.get("gateway", "default_channel", default=LOCAL_APP_CHANNEL) or LOCAL_APP_CHANNEL),
            "default_session_key": str(config.get("gateway", "default_session_key", default=LOCAL_APP_DEFAULT_SESSION) or LOCAL_APP_DEFAULT_SESSION),
            "session_router_enabled": _coerce_bool(
                config.get("gateway", "session_router_enabled", default=True),
                default=True,
            ),
            "connected_sessions": connected_sessions,
            "queued_notifications": queued_notifications,
            "delivered_notifications": delivered_notifications,
            "failed_notifications": failed_notifications,
            "channels": channels,
            "checked_at": _serialize_dt(_utcnow()),
        }

    async def notify(
        self,
        *,
        title: str,
        body: str = "",
        target: str | None = None,
        level: str = "info",
        payload: dict[str, Any] | None = None,
        source_type: str = "",
        source_id: str = "",
    ) -> dict[str, Any]:
        await self.initialize()
        channel, session_key = self._parse_target(
            target,
            default_channel=str(config.get("gateway", "default_channel", default=LOCAL_APP_CHANNEL) or LOCAL_APP_CHANNEL),
        )
        created_at = _serialize_dt(_utcnow())
        notification_id = f"ntf_{uuid.uuid4().hex[:12]}"
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO gateway_outbox (
                    notification_id, channel, session_key, level, title, body,
                    payload_json, source_type, source_id, status, attempts,
                    last_error, created_at, delivered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    channel,
                    session_key,
                    str(level or "info"),
                    str(title or "").strip() or "Notificacion",
                    str(body or ""),
                    json.dumps(payload or {}, ensure_ascii=False),
                    str(source_type or ""),
                    str(source_id or ""),
                    "queued",
                    0,
                    "",
                    created_at,
                    None,
                ),
            )
            await db.commit()

        await self._deliver_notification(notification_id)
        item = await self.get_outbox_item(notification_id)
        return item or {
            "notification_id": notification_id,
            "channel": channel,
            "session_key": session_key,
            "status": "queued",
            "title": title,
            "body": body,
            "payload": payload or {},
        }

    async def send_text_notification(
        self,
        channel: str,
        session_key: str,
        text: str,
        *,
        level: str = "info",
        source_type: str = "",
        source_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        merged_payload = {
            "render": "plain_text",
            "text": str(text or "").strip(),
        }
        if isinstance(payload, dict):
            merged_payload.update(payload)
        return await self.notify(
            title="G-Mini Agent",
            body=str(text or "").strip(),
            target=f"{_normalize_channel(channel)}:{_normalize_session_key(session_key)}",
            level=level,
            payload=merged_payload,
            source_type=source_type,
            source_id=source_id,
        )

    async def send_image_notification(
        self,
        channel: str,
        session_key: str,
        image_b64: str,
        *,
        caption: str = "",
        filename: str = "gmini-screenshot.png",
        mime_type: str = "image/png",
        level: str = "info",
        source_type: str = "",
        source_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        merged_payload = {
            "render": "image",
            "image_b64": str(image_b64 or "").strip(),
            "caption": str(caption or "").strip(),
            "filename": str(filename or "gmini-screenshot.png").strip() or "gmini-screenshot.png",
            "mime_type": str(mime_type or "image/png").strip() or "image/png",
        }
        if isinstance(payload, dict):
            merged_payload.update(payload)
        return await self.notify(
            title="Screenshot de G-Mini",
            body=str(caption or "").strip() or "Captura actual del agente.",
            target=f"{_normalize_channel(channel)}:{_normalize_session_key(session_key)}",
            level=level,
            payload=merged_payload,
            source_type=source_type,
            source_id=source_id,
        )

    async def get_outbox_item(self, notification_id: str) -> dict[str, Any] | None:
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM gateway_outbox WHERE notification_id = ?",
                (notification_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return self._row_to_outbox(dict(row)) if row else None

    async def deliver_pending(
        self,
        *,
        channel: str = LOCAL_APP_CHANNEL,
        session_key: str = LOCAL_APP_DEFAULT_SESSION,
        limit: int = 50,
    ) -> None:
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT notification_id
                FROM gateway_outbox
                WHERE status = 'queued' AND channel = ? AND session_key = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (_normalize_channel(channel), _normalize_session_key(session_key), max(1, min(int(limit), 500))),
            ) as cursor:
                rows = [dict(row) async for row in cursor]
        for row in rows:
            await self._deliver_notification(str(row["notification_id"]))

    async def notify_scheduler_run(
        self,
        *,
        job: dict[str, Any],
        run: dict[str, Any],
    ) -> list[dict[str, Any]]:
        await self.initialize()
        if not self.enabled:
            return []

        status = str(run.get("status", "") or "").strip().lower()
        success = status == "success"
        if success:
            target_specs = _coerce_list(
                config.get("gateway", "notifications", "scheduler_success_targets", default=[f"{LOCAL_APP_CHANNEL}:{LOCAL_APP_DEFAULT_SESSION}"])
            )
        else:
            target_specs = _coerce_list(
                config.get("gateway", "notifications", "scheduler_error_targets", default=[f"{LOCAL_APP_CHANNEL}:{LOCAL_APP_DEFAULT_SESSION}"])
            )
        if not target_specs:
            return []

        trigger_source = str(run.get("trigger_source", "") or "").strip() or "scheduler"
        title = (
            f"Job completado: {job.get('name') or job.get('job_id')}"
            if success
            else f"Job con error: {job.get('name') or job.get('job_id')}"
        )
        result = run.get("result") or {}
        retry_scheduled = bool(result.get("retry_scheduled"))
        body_parts = [
            f"Trigger: {trigger_source}",
            f"Estado: {status or 'desconocido'}",
        ]
        if retry_scheduled:
            body_parts.append(
                f"Retry #{int(result.get('retry_attempt') or 0)} en {int(result.get('retry_delay_seconds') or 0)}s"
            )
        if run.get("error"):
            body_parts.append(f"Error: {run.get('error')}")
        elif result.get("next_run_at"):
            body_parts.append(f"Proxima ejecucion: {result.get('next_run_at')}")

        payload = {
            "job_id": job.get("job_id"),
            "job_name": job.get("name"),
            "run_id": run.get("run_id"),
            "status": status,
            "trigger_source": trigger_source,
            "result": result,
            "error": run.get("error") or "",
        }
        delivered_items: list[dict[str, Any]] = []
        for target_spec in target_specs:
            delivered_items.append(
                await self.notify(
                    title=title,
                    body=" | ".join(part for part in body_parts if part),
                    target=target_spec,
                    level="success" if success else "error",
                    payload=payload,
                    source_type="scheduler",
                    source_id=str(run.get("run_id") or ""),
                )
            )
        return delivered_items

    async def _deliver_notification(self, notification_id: str) -> None:
        item = await self.get_outbox_item(notification_id)
        if not item:
            return

        channel = str(item.get("channel") or "")
        session_key = str(item.get("session_key") or LOCAL_APP_DEFAULT_SESSION)
        if not self._channel_enabled(channel):
            await self._mark_outbox_failed(notification_id, f"Canal deshabilitado: {channel}")
            return

        if channel == LOCAL_APP_CHANNEL:
            if self._sio is None:
                return

            sessions = await self.list_sessions(channel=channel, connected_only=True, limit=200)
            matching_sessions = [
                session for session in sessions if session.get("session_key") == session_key
            ]
            if not matching_sessions:
                return

            payload = {
                "notification_id": item["notification_id"],
                "channel": channel,
                "session_key": session_key,
                "level": item.get("level", "info"),
                "title": item.get("title", ""),
                "body": item.get("body", ""),
                "payload": item.get("payload", {}),
                "source_type": item.get("source_type", ""),
                "source_id": item.get("source_id", ""),
                "created_at": item.get("created_at"),
            }
            for session in matching_sessions:
                try:
                    await self._sio.emit("gateway:notification", payload, to=session["sid"])
                except Exception as exc:
                    logger.warning(f"Gateway local_app emit fallo para {session['sid']}: {exc}")
                    await self._mark_outbox_failed(notification_id, str(exc), increment_attempt=True)
                    return
            await self._mark_outbox_delivered(notification_id)
            return

        if channel == TELEGRAM_CHANNEL:
            try:
                await self._telegram.send_notification(item)
            except Exception as exc:
                logger.warning(f"Gateway telegram delivery fallo para {session_key}: {exc}")
                await self._mark_outbox_failed(notification_id, str(exc), increment_attempt=True)
                return
            await self._mark_outbox_delivered(notification_id)
            return

        if channel == DISCORD_CHANNEL:
            try:
                await self._discord.send_notification(item)
            except Exception as exc:
                logger.warning(f"Gateway discord delivery fallo para {session_key}: {exc}")
                await self._mark_outbox_failed(notification_id, str(exc), increment_attempt=True)
                return
            await self._mark_outbox_delivered(notification_id)
            return

        if channel == WHATSAPP_CHANNEL:
            try:
                await self._whatsapp.send_notification(item)
            except Exception as exc:
                logger.warning(f"Gateway whatsapp delivery fallo para {session_key}: {exc}")
                await self._mark_outbox_failed(notification_id, str(exc), increment_attempt=True)
                return
            await self._mark_outbox_delivered(notification_id)
            return

        if channel == SLACK_CHANNEL:
            try:
                await self._slack.send_notification(item)
            except Exception as exc:
                logger.warning(f"Gateway slack delivery fallo para {session_key}: {exc}")
                await self._mark_outbox_failed(notification_id, str(exc), increment_attempt=True)
                return
            await self._mark_outbox_delivered(notification_id)
            return

        await self._mark_outbox_failed(notification_id, f"Canal aun no implementado: {channel}")

    async def _mark_outbox_delivered(self, notification_id: str) -> None:
        delivered_at = _serialize_dt(_utcnow())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE gateway_outbox
                SET status = 'delivered', attempts = attempts + 1, last_error = '', delivered_at = ?
                WHERE notification_id = ?
                """,
                (delivered_at, notification_id),
            )
            await db.commit()

    async def _mark_outbox_failed(
        self,
        notification_id: str,
        error: str,
        *,
        increment_attempt: bool = False,
    ) -> None:
        delivered_at = _serialize_dt(_utcnow())
        async with aiosqlite.connect(self._db_path) as db:
            if increment_attempt:
                await db.execute(
                    """
                    UPDATE gateway_outbox
                    SET status = 'failed', attempts = attempts + 1, last_error = ?, delivered_at = ?
                    WHERE notification_id = ?
                    """,
                    (str(error or ""), delivered_at, notification_id),
                )
            else:
                await db.execute(
                    """
                    UPDATE gateway_outbox
                    SET status = 'failed', last_error = ?, delivered_at = ?
                    WHERE notification_id = ?
                    """,
                    (str(error or ""), delivered_at, notification_id),
                )
            await db.commit()

    async def forward_agent_message(
        self,
        sid: str,
        text: str,
        *,
        msg_type: str = "text",
        done: bool = False,
    ) -> bool:
        parsed = self.parse_virtual_sid(sid)
        if not parsed:
            self._stream_buffers.pop(sid, None)
            return False
        channel, session_key = parsed
        if msg_type == "text" and not done:
            self._stream_buffers[sid] = f"{self._stream_buffers.get(sid, '')}{text}"
            return True

        if done:
            buffered = self._stream_buffers.pop(sid, "")
            final_text = buffered or str(text or "").strip()
            if final_text:
                await self.send_text_notification(
                    channel,
                    session_key,
                    final_text,
                    level="info",
                    source_type="agent.message",
                )
            return True

        await self.send_text_notification(
            channel,
            session_key,
            str(text or "").strip(),
            level="error" if msg_type == "error" else "warning" if msg_type == "warning" else "info",
            source_type=f"agent.{msg_type}",
            payload={"message_type": msg_type},
        )
        return True

    async def forward_agent_status(self, sid: str, status: str) -> bool:
        return self.is_virtual_sid(sid)

    async def forward_agent_screenshot(
        self,
        sid: str,
        image_b64: str,
        *,
        caption: str = "",
    ) -> bool:
        parsed = self.parse_virtual_sid(sid)
        if not parsed:
            return False
        channel, session_key = parsed
        payload: dict[str, Any] = {}
        image_payload = str(image_b64 or "").strip()
        try:
            image_bytes = base64.b64decode(image_payload)
            artifact_path = self._persist_artifact_bytes(image_bytes, "gmini-screenshot.png")
            payload["image_path"] = str(artifact_path)
            image_payload = ""
        except Exception:
            payload["image_b64"] = image_payload
        await self.send_image_notification(
            channel,
            session_key,
            image_payload,
            caption=caption,
            source_type="agent.screenshot",
            payload=payload,
        )
        return True

    async def forward_agent_approval(
        self,
        sid: str,
        *,
        pending: bool,
        summary: str = "",
        findings: list[dict[str, Any]] | None = None,
        kind: str = "approval",
        decision: str | None = None,
        mode_name: str | None = None,
    ) -> bool:
        parsed = self.parse_virtual_sid(sid)
        if not parsed:
            return False
        channel, session_key = parsed
        if not pending:
            return True
        approval_token = ""
        if self._agent_core and hasattr(self._agent_core, "get_pending_approval_token"):
            try:
                approval_token = str(self._agent_core.get_pending_approval_token(sid) or "").strip()
            except Exception:
                approval_token = ""
        findings_lines = []
        for item in findings or []:
            findings_lines.append(
                f"- {item.get('action', '?')}: {item.get('reason', '?')}"
            )
        approve_callback = f"gmini:approve:{approval_token}" if approval_token else "gmini:approve"
        cancel_callback = f"gmini:cancel:{approval_token}" if approval_token else "gmini:cancel"
        parts = [
            "G-Mini necesita aprobacion para continuar." if kind == "approval" else "G-Mini requiere confirmar el dry-run antes de continuar.",
            f"Modo: {mode_name}" if mode_name else "",
            summary,
            "\n".join(findings_lines),
            "Responde /aprobar o /cancelar.",
        ]
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Aprobar", "callback_data": approve_callback},
                    {"text": "Cancelar", "callback_data": cancel_callback},
                ],
                [
                    {"text": "Estado", "callback_data": "gmini:status"},
                ],
            ]
        }
        await self.send_text_notification(
            channel,
            session_key,
            "\n\n".join(part for part in parts if part),
            level="warning",
            source_type="agent.approval",
            payload={
                "kind": kind,
                "decision": decision or "",
                "findings": findings or [],
                "reply_markup": reply_markup,
            },
        )
        return True

    def _row_to_session(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "sid": str(row.get("sid") or ""),
            "channel": str(row.get("channel") or ""),
            "session_key": str(row.get("session_key") or ""),
            "display_name": str(row.get("display_name") or ""),
            "connected": bool(row.get("connected")),
            "meta": self._safe_json_loads(row.get("meta_json"), {}),
            "connected_at": row.get("connected_at"),
            "last_seen_at": row.get("last_seen_at"),
            "disconnected_at": row.get("disconnected_at"),
        }

    def _row_to_outbox(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "notification_id": str(row.get("notification_id") or ""),
            "channel": str(row.get("channel") or ""),
            "session_key": str(row.get("session_key") or ""),
            "level": str(row.get("level") or "info"),
            "title": str(row.get("title") or ""),
            "body": str(row.get("body") or ""),
            "payload": self._safe_json_loads(row.get("payload_json"), {}),
            "source_type": str(row.get("source_type") or ""),
            "source_id": str(row.get("source_id") or ""),
            "status": str(row.get("status") or "queued"),
            "attempts": int(row.get("attempts") or 0),
            "last_error": str(row.get("last_error") or ""),
            "created_at": row.get("created_at"),
            "delivered_at": row.get("delivered_at"),
        }

    @staticmethod
    def _safe_json_loads(raw: Any, default: Any) -> Any:
        if raw in (None, ""):
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default


_gateway: GatewayService | None = None


def get_gateway() -> GatewayService:
    global _gateway
    if _gateway is None:
        _gateway = GatewayService()
    return _gateway
