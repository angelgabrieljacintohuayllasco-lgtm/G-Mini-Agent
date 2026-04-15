"""
G-Mini Agent - Conector Discord para GatewayService.
Entrega notificaciones, enruta mensajes remotos y procesa comandos basicos.
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from backend.config import ROOT_DIR, config

try:  # pragma: no cover - dependencia opcional
    import discord as discord_lib
except Exception:  # pragma: no cover - entorno sin discord.py
    discord_lib = None

if TYPE_CHECKING:
    from backend.core.gateway_service import GatewayService


DISCORD_CHANNEL = "discord"
DEFAULT_DISCORD_TOKEN_VAULT = "discord_bot"
DISCORD_INBOX_DIR = ROOT_DIR / "data" / "gateway" / "discord" / "inbox"
MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024
MAX_TEXT_CHUNK = 1800


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    return []


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


def _sanitize_filename(value: str, fallback: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._")
    return candidate or fallback


class DiscordGatewayConnector:
    def __init__(self, gateway: "GatewayService"):
        self._gateway = gateway
        self._client = None
        self._task: asyncio.Task | None = None
        self._bot_user: str = ""
        self._bot_user_id: str = ""
        self._last_error: str = ""
        self._last_status: str = "stopped"
        self._fake_running = False
        self._stop_requested = False

    @property
    def _channel_config(self) -> dict[str, Any]:
        raw = config.get("gateway", "channels", DISCORD_CHANNEL, default={}) or {}
        return raw if isinstance(raw, dict) else {}

    @property
    def bot_token_vault(self) -> str:
        return str(
            self._channel_config.get("bot_token_vault") or DEFAULT_DISCORD_TOKEN_VAULT
        ).strip() or DEFAULT_DISCORD_TOKEN_VAULT

    @property
    def bot_token(self) -> str:
        return str(config.get_api_key(self.bot_token_vault) or "").strip()

    @property
    def default_channel_id(self) -> str:
        return str(self._channel_config.get("default_channel_id") or "").strip()

    @property
    def allowed_guild_ids(self) -> list[str]:
        return _coerce_list(self._channel_config.get("allowed_guild_ids", []))

    @property
    def allowed_channel_ids(self) -> list[str]:
        return _coerce_list(self._channel_config.get("allowed_channel_ids", []))

    @property
    def group_activation_aliases(self) -> list[str]:
        aliases = _coerce_list(self._channel_config.get("group_activation_aliases", []))
        return aliases or ["g-mini", "gmini", "agente"]

    @property
    def fake_mode(self) -> bool:
        env_value = os.getenv("GMINI_DISCORD_FAKE")
        if env_value is not None:
            return _coerce_bool(env_value, default=False)
        return _coerce_bool(self._channel_config.get("fake_mode"), default=False)

    @property
    def inbox_dir(self) -> Path:
        DISCORD_INBOX_DIR.mkdir(parents=True, exist_ok=True)
        return DISCORD_INBOX_DIR

    @property
    def enabled(self) -> bool:
        return self._gateway.channel_enabled(DISCORD_CHANNEL)

    @property
    def running(self) -> bool:
        return self._fake_running or (self._task is not None and not self._task.done())

    @property
    def ready(self) -> bool:
        return self._fake_running or (self.running and bool(self._bot_user_id))

    def get_status_detail(self) -> str:
        if not self.enabled:
            return "Canal deshabilitado."
        if self.fake_mode:
            return "Runtime fake de Discord operativo para pruebas."
        if discord_lib is None:
            return "Falta instalar discord.py en el backend."
        if not self.bot_token:
            return "Falta bot token de Discord en vault."
        if self.ready:
            return f"Bot Discord operativo como {self._bot_user or 'usuario desconocido'}."
        if self.running:
            return f"Bot Discord iniciado ({self._last_status})."
        if self._last_error:
            return f"Bot Discord detenido por error reciente: {self._last_error}"
        return "Bot Discord configurado pero inactivo."

    async def start(self) -> None:
        if not self.enabled or self.running:
            return

        self._stop_requested = False
        self._last_error = ""
        self._bot_user = ""
        self._bot_user_id = ""

        if self.fake_mode:
            self._fake_running = True
            self._last_status = "ready"
            self._bot_user = "Fake Discord Gateway"
            self._bot_user_id = "fake"
            await self._update_runtime_state()
            logger.info("Gateway Discord iniciado en modo fake")
            return

        if discord_lib is None:
            self._last_status = "error"
            self._last_error = "discord.py no esta instalado."
            await self._update_runtime_state()
            return

        if not self.bot_token:
            self._last_status = "error"
            self._last_error = "Falta bot token de Discord en vault."
            await self._update_runtime_state()
            return

        intents = discord_lib.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        try:
            intents.dm_messages = True
        except Exception:
            pass

        client = discord_lib.Client(intents=intents)
        self._bind_client_events(client)
        self._client = client
        self._last_status = "starting"
        await self._update_runtime_state()
        self._task = asyncio.create_task(self._run_client(), name="gateway-discord")
        logger.info("Gateway Discord iniciado")

    async def stop(self) -> None:
        self._stop_requested = True

        if self._fake_running:
            self._fake_running = False
            self._last_status = "stopped"
            self._bot_user = ""
            self._bot_user_id = ""
            await self._update_runtime_state()
            logger.info("Gateway Discord fake detenido")
            return

        client = self._client
        task = self._task
        self._client = None
        self._task = None
        self._bot_user = ""
        self._bot_user_id = ""
        self._last_status = "stopped"

        if client is not None:
            try:
                await client.close()
            except Exception:
                pass
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        await self._update_runtime_state()
        logger.info("Gateway Discord detenido")

    async def send_notification(self, item: dict[str, Any]) -> None:
        channel_id = self.resolve_channel_id(str(item.get("session_key") or ""))
        if not channel_id:
            raise RuntimeError("No se pudo resolver el channel_id de Discord para la notificacion.")

        if self.fake_mode:
            await self._update_runtime_state(
                {
                    "last_notification": {
                        "channel_id": channel_id,
                        "title": str(item.get("title") or ""),
                        "render": str((item.get("payload") or {}).get("render") or ""),
                    }
                }
            )
            return

        channel = await self._get_channel(channel_id)
        if channel is None or not hasattr(channel, "send"):
            raise RuntimeError(f"No se pudo abrir el canal de Discord: {channel_id}")

        payload = item.get("payload") or {}
        render = str(payload.get("render") or "").strip().lower()
        if render == "image":
            await self._send_media_notification(channel, item, media_kind="image")
            return
        if render in {"file", "document"}:
            await self._send_media_notification(channel, item, media_kind="document")
            return

        text = self._render_notification_text(item)
        if not text:
            raise RuntimeError("La notificacion de Discord no tiene texto para enviar.")
        chunks = self._split_text_chunks(text)
        # Si hay muchos chunks, crear un thread para no inundar el canal
        if len(chunks) > 3 and hasattr(channel, "create_thread"):
            thread_name = str(item.get("title") or text[:90]).strip()[:95]
            if len(thread_name) > 92:
                thread_name = thread_name[:92] + "..."
            try:
                # Enviar primer mensaje al canal y crear thread a partir de él
                first_msg = await channel.send(chunks[0])
                thread = await first_msg.create_thread(name=thread_name, auto_archive_duration=60)
                for chunk in chunks[1:]:
                    await thread.send(chunk)
                return
            except Exception:
                pass  # Fallback a envío normal
        for chunk in chunks:
            await channel.send(chunk)

    async def _run_client(self) -> None:
        try:
            if self._client is None:
                raise RuntimeError("Cliente Discord no inicializado.")
            await self._client.start(self.bot_token)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
            self._last_status = "error"
            await self._update_runtime_state()
            logger.warning(f"Gateway Discord detenido por error: {exc}")
            raise
        finally:
            if not self._stop_requested and self._last_status not in {"error", "ready"}:
                self._last_status = "stopped"
                await self._update_runtime_state()

    def _bind_client_events(self, client) -> None:
        @client.event
        async def on_ready():
            user = getattr(client, "user", None)
            self._bot_user = str(user or "").strip()
            self._bot_user_id = str(getattr(user, "id", "") or "").strip()
            self._last_status = "ready"
            self._last_error = ""
            await self._update_runtime_state({"guild_count": len(getattr(client, "guilds", []) or [])})
            logger.info(f"Gateway Discord listo como {self._bot_user or 'bot sin nombre'}")

        @client.event
        async def on_message(message):
            await self._handle_discord_message(message)

        @client.event
        async def on_disconnect():
            if self._stop_requested:
                return
            self._last_status = "disconnected"
            await self._update_runtime_state()

        @client.event
        async def on_resumed():
            self._last_status = "ready"
            await self._update_runtime_state()

    async def _handle_discord_message(self, message) -> None:
        if message is None:
            return
        author = getattr(message, "author", None)
        if author is None or getattr(author, "bot", False):
            return
        if self._bot_user_id and str(getattr(author, "id", "") or "").strip() == self._bot_user_id:
            return

        text = str(getattr(message, "content", "") or "").strip()
        attachments = await self._extract_attachments(getattr(message, "attachments", []) or [])
        if not text and not attachments:
            return

        guild = getattr(message, "guild", None)
        channel = getattr(message, "channel", None)
        channel_id = str(getattr(channel, "id", "") or "").strip()
        guild_id = str(getattr(guild, "id", "") or "").strip()
        if not channel_id:
            return
        if self.allowed_channel_ids and channel_id not in self.allowed_channel_ids:
            return
        if guild_id and self.allowed_guild_ids and guild_id not in self.allowed_guild_ids:
            return

        payload = {
            "channel_id": channel_id,
            "guild_id": guild_id,
            "guild_name": str(getattr(guild, "name", "") or ""),
            "channel_name": str(getattr(channel, "name", "") or ""),
            "channel_type": "guild" if guild_id else "dm",
            "author_id": str(getattr(author, "id", "") or "").strip(),
            "author_name": str(
                getattr(author, "display_name", None) or getattr(author, "name", "") or channel_id
            ).strip(),
            "text": text,
            "attachments": attachments,
        }
        await self._process_message_payload(payload)

    async def _process_message_payload(self, payload: dict[str, Any]) -> None:
        channel_id = str(payload.get("channel_id") or "").strip()
        text = str(payload.get("text") or "").strip()
        attachments = payload.get("attachments") or []
        if not channel_id or (not text and not attachments):
            return

        guild_id = str(payload.get("guild_id") or "").strip()
        channel_type = str(payload.get("channel_type") or "dm").strip().lower()
        session_key = self._build_session_key(guild_id, channel_id)
        display_name = str(payload.get("author_name") or channel_id).strip() or channel_id
        meta = {
            "channel_id": channel_id,
            "guild_id": guild_id,
            "guild_name": str(payload.get("guild_name") or ""),
            "channel_name": str(payload.get("channel_name") or ""),
            "author_id": str(payload.get("author_id") or ""),
            "author_name": display_name,
            "channel_type": channel_type,
        }
        await self._gateway.register_remote_session(
            DISCORD_CHANNEL,
            session_key=session_key,
            display_name=display_name,
            meta=meta,
        )

        if guild_id and not self._should_process_group_message(text):
            return

        cleaned_text = self._normalize_group_text(text)
        if cleaned_text.startswith("/"):
            await self._handle_command(session_key, channel_id, cleaned_text)
            return

        if self._gateway.agent_core is None:
            await self._send_session_text(session_key, "El backend del agente no esta disponible todavia.")
            return

        await self._gateway.agent_core.process_gateway_message(
            DISCORD_CHANNEL,
            session_key,
            cleaned_text or text,
            attachments=attachments if isinstance(attachments, list) else [],
        )

    async def _handle_command(self, session_key: str, channel_id: str, text: str) -> None:
        command_text = text.split(None, 1)
        raw_command = command_text[0].strip().lower()
        args = command_text[1].strip() if len(command_text) > 1 else ""
        command = raw_command.split("@", 1)[0]
        agent = self._gateway.agent_core
        sid = self._gateway.build_virtual_sid(DISCORD_CHANNEL, session_key)

        if command in {"/help", "/ayuda"}:
            await self._send_session_text(session_key, self._build_help_text())
            return

        if command in {"/estado", "/status"}:
            await self._send_session_text(session_key, self._build_status_text())
            return

        if command in {"/start", "/resume", "/reanudar"}:
            if agent is not None:
                await agent.resume()
            await self._send_session_text(session_key, "Agente reanudado.\n\n" + self._build_help_text())
            return

        if command == "/pause":
            if agent is not None:
                await agent.pause()
            await self._send_session_text(session_key, "Agente pausado.")
            return

        if command == "/stop":
            if agent is not None:
                await agent.stop()
            await self._send_session_text(session_key, "Stop solicitado al agente.")
            return

        if command in {"/aprobar", "/approve"}:
            if agent is None:
                await self._send_session_text(session_key, "El backend del agente no esta disponible.")
                return
            approved = await agent.approve_pending(sid, token=args or None)
            await self._send_session_text(
                session_key,
                "Aprobacion enviada." if approved else "No habia una aprobacion valida pendiente.",
            )
            return

        if command in {"/cancelar", "/reject", "/deny"}:
            if agent is None:
                await self._send_session_text(session_key, "El backend del agente no esta disponible.")
                return
            rejected = await agent.reject_pending(sid, token=args or None)
            await self._send_session_text(
                session_key,
                "Solicitud cancelada." if rejected else "No habia una solicitud valida pendiente.",
            )
            return

        if command == "/modo":
            if agent is None:
                await self._send_session_text(session_key, "El backend del agente no esta disponible.")
                return
            if not args:
                await self._send_session_text(
                    session_key,
                    "Indica un modo. Ejemplo: /modo programador",
                )
                return
            try:
                result = await agent.set_gateway_session_mode(DISCORD_CHANNEL, session_key, args)
            except Exception as exc:
                await self._send_session_text(session_key, f"No se pudo cambiar el modo: {exc}")
                return
            await self._send_session_text(
                session_key,
                f"Modo actualizado a {result.get('mode_name') or result.get('mode')}.",
            )
            return

        await self._send_session_text(session_key, self._build_help_text())

    async def _send_session_text(self, session_key: str, text: str) -> None:
        await self._gateway.send_text_notification(
            DISCORD_CHANNEL,
            session_key,
            text,
            level="info",
            source_type="gateway.discord",
        )

    def _build_help_text(self) -> str:
        return (
            "Comandos disponibles:\n"
            "/estado\n"
            "/start\n"
            "/pause\n"
            "/stop\n"
            "/aprobar [token]\n"
            "/cancelar [token]\n"
            "/modo <nombre>\n\n"
            "En canales de servidor solo respondo si me mencionan o si usas un alias configurado."
        )

    def _build_status_text(self) -> str:
        agent = self._gateway.agent_core
        if agent is None:
            return "Backend no disponible."
        status = agent.get_status()
        return (
            f"Estado: {'pausado' if status.get('paused') else 'activo' if status.get('running') else 'detenido'}\n"
            f"Modo: {status.get('mode_name') or status.get('mode')}\n"
            f"Modelo: {status.get('provider') or '-'} / {status.get('model') or '-'}\n"
            f"Subagentes activos: {status.get('subagents_active', 0)}\n"
            f"Terminales activas: {status.get('terminals_active', 0)}\n"
            f"Aprobacion pendiente: {'si' if status.get('pending_approval') else 'no'}"
        )

    def _should_process_group_message(self, text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if normalized.startswith("/"):
            return True
        if self._bot_user_id:
            if f"<@{self._bot_user_id}>" in normalized or f"<@!{self._bot_user_id}>" in normalized:
                return True
        return any(alias.lower() in normalized for alias in self.group_activation_aliases if alias)

    def _normalize_group_text(self, text: str) -> str:
        normalized = str(text or "")
        if self._bot_user_id:
            normalized = re.sub(rf"^<@!?{re.escape(self._bot_user_id)}>\s*", "", normalized).strip()
        return normalized.strip()

    def _build_session_key(self, guild_id: str, channel_id: str) -> str:
        if guild_id:
            return f"guild:{guild_id}:{channel_id}"
        return f"dm:{channel_id}"

    def resolve_channel_id(self, session_key: str) -> str:
        normalized = str(session_key or "").strip()
        if not normalized or normalized == "main":
            return self.default_channel_id
        if ":" in normalized:
            return str(normalized.rsplit(":", 1)[-1] or "").strip()
        return normalized

    async def _get_channel(self, channel_id: str):
        if self._client is None:
            raise RuntimeError("Cliente Discord no inicializado.")
        try:
            numeric_id = int(str(channel_id or "").strip())
        except ValueError as exc:
            raise RuntimeError(f"channel_id de Discord invalido: {channel_id}") from exc
        channel = self._client.get_channel(numeric_id)
        if channel is not None:
            return channel
        return await self._client.fetch_channel(numeric_id)

    async def _send_media_notification(self, channel, item: dict[str, Any], *, media_kind: str) -> None:
        payload = item.get("payload") or {}
        caption = str(payload.get("caption") or item.get("body") or item.get("title") or "").strip()
        if media_kind == "image":
            data_b64 = str(payload.get("image_b64") or payload.get("photo_b64") or "").strip()
            file_path = str(payload.get("image_path") or "").strip()
            default_name = "gmini-image.png"
        else:
            data_b64 = str(payload.get("file_b64") or "").strip()
            file_path = str(payload.get("file_path") or "").strip()
            default_name = "gmini-document.bin"

        filename = _sanitize_filename(
            str(payload.get("filename") or Path(file_path).name or default_name),
            default_name,
        )

        file_bytes: bytes | None = None
        if data_b64:
            try:
                file_bytes = base64.b64decode(data_b64)
            except Exception as exc:
                raise RuntimeError("No se pudo decodificar el adjunto de Discord.") from exc
        elif file_path:
            candidate = Path(file_path)
            if not candidate.exists():
                raise RuntimeError(f"No existe el archivo a enviar por Discord: {candidate}")
            file_bytes = candidate.read_bytes()
        else:
            text = self._render_notification_text(item)
            if text:
                for chunk in self._split_text_chunks(text):
                    await channel.send(chunk)
                return
            raise RuntimeError("La notificacion multimedia de Discord no tiene contenido utilizable.")

        if file_bytes is None:
            raise RuntimeError("No se pudo preparar el archivo para Discord.")

        file_obj = discord_lib.File(fp=io.BytesIO(file_bytes), filename=filename)
        try:
            await channel.send(content=caption or None, file=file_obj)
        finally:
            try:
                file_obj.close()
            except Exception:
                pass

    async def _extract_attachments(self, raw_attachments: list[Any]) -> list[dict[str, Any]]:
        attachments: list[dict[str, Any]] = []
        for index, attachment in enumerate(raw_attachments or [], start=1):
            filename = _sanitize_filename(
                str(getattr(attachment, "filename", "") or f"discord_attachment_{index}"),
                f"discord_attachment_{index}",
            )
            mime_type = str(getattr(attachment, "content_type", "") or "application/octet-stream").strip()
            size = int(getattr(attachment, "size", 0) or 0)
            try:
                data = await attachment.read(use_cached=True)
            except Exception:
                try:
                    data = await attachment.read()
                except Exception as exc:
                    logger.warning(f"No se pudo descargar adjunto de Discord {filename}: {exc}")
                    continue
            artifact_path = self._gateway._persist_artifact_bytes(data, filename)
            if mime_type.startswith("image/"):
                kind = "image"
            elif mime_type.startswith("audio/"):
                kind = "audio"
            elif mime_type.startswith("video/"):
                kind = "video"
            elif mime_type in {"application/pdf", "text/plain"}:
                kind = "document"
            else:
                kind = "file"
            item: dict[str, Any] = {
                "kind": kind,
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": size or len(data),
                "local_path": str(artifact_path),
                "caption": "",
                "source_channel": DISCORD_CHANNEL,
            }
            if kind == "image" and len(data) <= MAX_INLINE_IMAGE_BYTES:
                item["image_base64"] = base64.b64encode(data).decode("ascii")
            attachments.append(item)
        return attachments

    def _split_text_chunks(self, text: str) -> list[str]:
        normalized = str(text or "").strip()
        if len(normalized) <= MAX_TEXT_CHUNK:
            return [normalized] if normalized else []
        chunks: list[str] = []
        remaining = normalized
        while remaining:
            if len(remaining) <= MAX_TEXT_CHUNK:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, MAX_TEXT_CHUNK)
            if split_at <= 0:
                split_at = remaining.rfind(" ", 0, MAX_TEXT_CHUNK)
            if split_at <= 0:
                split_at = MAX_TEXT_CHUNK
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        return [chunk for chunk in chunks if chunk]

    async def _update_runtime_state(self, extra: dict[str, Any] | None = None) -> None:
        payload = {
            "status": self._last_status,
            "error": self._last_error,
            "bot_user": self._bot_user,
            "bot_user_id": self._bot_user_id,
            "default_channel_id": self.default_channel_id,
            "allowed_guild_ids": self.allowed_guild_ids,
            "allowed_channel_ids": self.allowed_channel_ids,
            "fake_mode": self.fake_mode,
        }
        if isinstance(extra, dict):
            payload.update(extra)
        await self._gateway.set_state_value("discord_runtime", payload)

    def _render_notification_text(self, item: dict[str, Any]) -> str:
        payload = item.get("payload") or {}
        plain_text = str(payload.get("text") or "").strip()
        if plain_text:
            return plain_text
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or "").strip()
        if title and body:
            return f"{title}\n{body}"
        return title or body
