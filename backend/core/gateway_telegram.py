"""
G-Mini Agent - Conector Telegram para GatewayService.
Entrega notificaciones, hace long polling y enruta comandos básicos.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
from loguru import logger

from backend.config import ROOT_DIR, config

if TYPE_CHECKING:
    from backend.core.gateway_service import GatewayService


TELEGRAM_CHANNEL = "telegram"
DEFAULT_BOT_TOKEN_VAULT = "telegram_bot"
DEFAULT_BASE_URL = "https://api.telegram.org"
TELEGRAM_INBOX_DIR = ROOT_DIR / "data" / "gateway" / "telegram" / "inbox"
MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = str(value).strip()
        return [normalized] if normalized else []
    return []


def _coerce_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _sanitize_filename(value: str, fallback: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._")
    return candidate or fallback


class TelegramGatewayConnector:
    def __init__(self, gateway: "GatewayService"):
        self._gateway = gateway
        self._task: asyncio.Task | None = None
        self._bot_username: str = ""
        self._last_error: str = ""

    @property
    def _channel_config(self) -> dict[str, Any]:
        raw = config.get("gateway", "channels", TELEGRAM_CHANNEL, default={}) or {}
        return raw if isinstance(raw, dict) else {}

    @property
    def bot_token_vault(self) -> str:
        return str(
            self._channel_config.get("bot_token_vault") or DEFAULT_BOT_TOKEN_VAULT
        ).strip() or DEFAULT_BOT_TOKEN_VAULT

    @property
    def bot_token(self) -> str:
        return str(config.get_api_key(self.bot_token_vault) or "").strip()

    @property
    def base_url(self) -> str:
        return str(self._channel_config.get("base_url") or DEFAULT_BASE_URL).rstrip("/")

    @property
    def inbox_dir(self) -> Path:
        TELEGRAM_INBOX_DIR.mkdir(parents=True, exist_ok=True)
        return TELEGRAM_INBOX_DIR

    @property
    def group_activation_aliases(self) -> list[str]:
        aliases = _coerce_list(self._channel_config.get("group_activation_aliases", []))
        return aliases or ["g-mini", "gmini", "agente"]

    @property
    def default_chat_id(self) -> str:
        return str(self._channel_config.get("default_chat_id") or "").strip()

    @property
    def allowed_chat_ids(self) -> list[str]:
        return _coerce_list(self._channel_config.get("allowed_chat_ids", []))

    @property
    def poll_interval_seconds(self) -> float:
        return _coerce_float(self._channel_config.get("poll_interval_seconds"), 3.0)

    @property
    def long_poll_timeout_seconds(self) -> float:
        return _coerce_float(self._channel_config.get("long_poll_timeout_seconds"), 20.0)

    @property
    def enabled(self) -> bool:
        return self._gateway.channel_enabled(TELEGRAM_CHANNEL) and bool(self.bot_token)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def get_status_detail(self) -> str:
        if not self._gateway.channel_enabled(TELEGRAM_CHANNEL):
            return "Canal deshabilitado."
        if not self.bot_token:
            return "Falta bot token de Telegram en vault."
        if self.running:
            return "Bot operativo por long polling."
        if self._last_error:
            return f"Bot detenido por error reciente: {self._last_error}"
        return "Bot configurado pero polling inactivo."

    async def start(self) -> None:
        if not self.enabled or self.running:
            return
        self._task = asyncio.create_task(self._run_loop(), name="gateway-telegram")
        logger.info("Gateway Telegram polling iniciado")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Gateway Telegram polling detenido")

    def resolve_chat_id(self, session_key: str) -> str:
        normalized = str(session_key or "").strip()
        if not normalized or normalized == "main":
            return self.default_chat_id
        if ":" in normalized:
            _, chat_id = normalized.rsplit(":", 1)
            return str(chat_id or "").strip()
        return normalized

    async def send_notification(self, item: dict[str, Any]) -> None:
        chat_id = self.resolve_chat_id(str(item.get("session_key") or ""))
        if not chat_id:
            raise RuntimeError("No se pudo resolver el chat_id de Telegram para la notificacion.")
        payload = item.get("payload") or {}
        render = str(payload.get("render") or "").strip().lower()
        if render == "image":
            await self._send_image_notification(chat_id, item)
            return
        if render in {"file", "document"}:
            await self._send_document_notification(chat_id, item)
            return

        text = self._render_notification_text(item)
        if not text:
            raise RuntimeError("La notificacion de Telegram no tiene texto para enviar.")
        reply_markup = payload.get("reply_markup") if isinstance(payload, dict) else None
        await self._send_raw_text(chat_id, text, reply_markup=reply_markup if isinstance(reply_markup, dict) else None)

    async def _run_loop(self) -> None:
        offset = int(await self._gateway.get_state_value("telegram_last_update_id", 0) or 0)
        try:
            await self._ensure_bot_identity()
            while True:
                updates = await self._fetch_updates(offset)
                if not updates:
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue
                for update in updates:
                    update_id = int(update.get("update_id") or 0)
                    if update_id:
                        offset = max(offset, update_id + 1)
                        await self._gateway.set_state_value("telegram_last_update_id", offset)
                    await self._handle_update(update)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
            logger.warning(f"Gateway Telegram detenido por error: {exc}")
            raise

    async def _ensure_bot_identity(self) -> None:
        try:
            response = await self._telegram_api("getMe", {})
        except Exception as exc:
            logger.warning(f"No se pudo obtener identidad de Telegram: {exc}")
            return
        result = response.get("result") if isinstance(response, dict) else {}
        self._bot_username = str((result or {}).get("username") or "").strip().lower()

    async def _fetch_updates(self, offset: int) -> list[dict[str, Any]]:
        response = await self._telegram_api(
            "getUpdates",
            {
                "offset": offset,
                "timeout": int(self.long_poll_timeout_seconds),
                "allowed_updates": ["message", "edited_message", "callback_query"],
            },
            timeout=self.long_poll_timeout_seconds + 5.0,
        )
        result = response.get("result") if isinstance(response, dict) else []
        return result if isinstance(result, list) else []

    async def _handle_update(self, update: dict[str, Any]) -> None:
        callback_query = update.get("callback_query")
        if isinstance(callback_query, dict):
            await self._handle_callback_query(callback_query)
            return

        message = update.get("message") or update.get("edited_message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat") or {}
        text = str(message.get("text") or message.get("caption") or "").strip()
        attachments = await self._extract_attachments(message)
        if not text and not attachments:
            return

        chat_id = str(chat.get("id") or "").strip()
        if not chat_id:
            return

        if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
            await self._send_raw_text(chat_id, "Chat no autorizado para controlar G-Mini Agent.")
            return

        chat_type = str(chat.get("type") or "private").strip().lower()
        session_key = self._build_session_key(chat_type, chat_id)
        display_name = self._build_display_name(chat)
        meta = {
            "chat_id": chat_id,
            "chat_type": chat_type,
            "title": str(chat.get("title") or ""),
            "username": str(chat.get("username") or ""),
            "first_name": str(chat.get("first_name") or ""),
            "last_name": str(chat.get("last_name") or ""),
        }
        await self._gateway.register_remote_session(
            TELEGRAM_CHANNEL,
            session_key=session_key,
            display_name=display_name,
            meta=meta,
        )

        if chat_type != "private" and not self._should_process_group_message(text):
            return

        if text.startswith("/"):
            await self._handle_command(session_key, chat_id, text)
            return

        if self._gateway.agent_core is None:
            await self._send_session_text(session_key, "El backend del agente no esta disponible todavia.")
            return

        await self._gateway.agent_core.process_gateway_message(
            TELEGRAM_CHANNEL,
            session_key,
            text,
            attachments=attachments,
        )

    async def _handle_callback_query(self, callback_query: dict[str, Any]) -> None:
        data = str(callback_query.get("data") or "").strip()
        action, callback_token = self._parse_callback_data(data)
        callback_id = str(callback_query.get("id") or "").strip()
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "").strip()
        if not callback_id or not chat_id:
            return

        if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
            await self._answer_callback_query(
                callback_id,
                text="Chat no autorizado para controlar G-Mini Agent.",
                show_alert=True,
            )
            return

        chat_type = str(chat.get("type") or "private").strip().lower()
        session_key = self._build_session_key(chat_type, chat_id)
        display_name = self._build_display_name(chat)
        meta = {
            "chat_id": chat_id,
            "chat_type": chat_type,
            "title": str(chat.get("title") or ""),
            "username": str(chat.get("username") or ""),
            "first_name": str(chat.get("first_name") or ""),
            "last_name": str(chat.get("last_name") or ""),
        }
        await self._gateway.register_remote_session(
            TELEGRAM_CHANNEL,
            session_key=session_key,
            display_name=display_name,
            meta=meta,
        )

        agent = self._gateway.agent_core
        sid = self._gateway.build_virtual_sid(TELEGRAM_CHANNEL, session_key)
        answer_text = "Accion no reconocida."
        clear_markup = False

        if action == "gmini:approve":
            if agent is None:
                answer_text = "El backend del agente no esta disponible."
            else:
                approved = await agent.approve_pending(sid, token=callback_token)
                answer_text = "Aprobacion enviada." if approved else "Esta aprobacion ya no es valida."
                clear_markup = approved
        elif action == "gmini:cancel":
            if agent is None:
                answer_text = "El backend del agente no esta disponible."
            else:
                rejected = await agent.reject_pending(sid, token=callback_token)
                answer_text = "Acciones canceladas." if rejected else "Esta cancelacion ya no es valida."
                clear_markup = rejected
        elif action == "gmini:pause":
            if agent is None:
                answer_text = "El backend del agente no esta disponible."
            else:
                await agent.pause()
                answer_text = "Agente pausado."
        elif action == "gmini:start":
            if agent is None:
                answer_text = "El backend del agente no esta disponible."
            else:
                await agent.resume()
                answer_text = "Agente reanudado."
        elif action == "gmini:stop":
            if agent is None:
                answer_text = "El backend del agente no esta disponible."
            else:
                await agent.stop()
                answer_text = "Stop solicitado."
        elif action == "gmini:status":
            answer_text = self._build_status_text()
            await self._send_session_text(
                session_key,
                answer_text,
                reply_markup=self._build_status_inline_keyboard(),
            )
            answer_text = "Estado enviado."

        await self._answer_callback_query(callback_id, text=answer_text[:180])
        if clear_markup:
            message_id = message.get("message_id")
            if message_id is not None:
                await self._clear_message_reply_markup(chat_id, int(message_id))

    async def _extract_attachments(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        attachments: list[dict[str, Any]] = []
        caption = str(message.get("caption") or "").strip()

        photo_items = message.get("photo")
        if isinstance(photo_items, list) and photo_items:
            photo = next(
                (
                    item
                    for item in reversed(photo_items)
                    if isinstance(item, dict) and item.get("file_id")
                ),
                None,
            )
            if photo:
                attachment = await self._download_attachment(
                    file_id=str(photo.get("file_id") or "").strip(),
                    fallback_name=f"telegram_photo_{photo.get('file_unique_id') or photo.get('file_id') or 'image'}.jpg",
                    mime_type="image/jpeg",
                    kind="image",
                    caption=caption,
                )
                if attachment:
                    attachments.append(attachment)

        document = message.get("document")
        if isinstance(document, dict) and document.get("file_id"):
            attachment = await self._download_attachment(
                file_id=str(document.get("file_id") or "").strip(),
                fallback_name=str(document.get("file_name") or "telegram_document.bin"),
                mime_type=str(document.get("mime_type") or "application/octet-stream"),
                kind="file",
                caption=caption,
            )
            if attachment:
                attachments.append(attachment)

        # Audio, voice, video, video_note
        for media_key, default_kind, default_mime, ext in [
            ("audio", "audio", "audio/mpeg", "mp3"),
            ("voice", "audio", "audio/ogg", "ogg"),
            ("video", "video", "video/mp4", "mp4"),
            ("video_note", "video", "video/mp4", "mp4"),
        ]:
            media = message.get(media_key)
            if isinstance(media, dict) and media.get("file_id"):
                attachment = await self._download_attachment(
                    file_id=str(media["file_id"]),
                    fallback_name=f"telegram_{media_key}_{media.get('file_unique_id', 'media')}.{ext}",
                    mime_type=str(media.get("mime_type") or default_mime),
                    kind=default_kind,
                    caption=caption,
                )
                if attachment:
                    attachments.append(attachment)

        return attachments

    async def _download_attachment(
        self,
        *,
        file_id: str,
        fallback_name: str,
        mime_type: str,
        kind: str,
        caption: str = "",
    ) -> dict[str, Any] | None:
        if not file_id:
            return None
        try:
            file_meta = await self._telegram_api("getFile", {"file_id": file_id})
            result = file_meta.get("result") if isinstance(file_meta, dict) else {}
            remote_path = str((result or {}).get("file_path") or "").strip()
            if not remote_path:
                raise RuntimeError("Telegram no devolvio file_path para el adjunto.")
            file_bytes = await self._download_file_bytes(remote_path)
        except Exception as exc:
            logger.warning(f"No se pudo descargar adjunto de Telegram {file_id}: {exc}")
            return None

        safe_name = _sanitize_filename(Path(remote_path).name or fallback_name, fallback_name)
        local_path = self.inbox_dir / safe_name
        counter = 1
        while local_path.exists():
            local_path = self.inbox_dir / f"{local_path.stem}_{counter}{local_path.suffix}"
            counter += 1
        local_path.write_bytes(file_bytes)

        attachment = {
            "kind": kind,
            "source": TELEGRAM_CHANNEL,
            "file_id": file_id,
            "file_name": local_path.name,
            "mime_type": mime_type,
            "size_bytes": len(file_bytes),
            "local_path": str(local_path),
            "caption": caption,
            "remote_path": remote_path,
        }
        if mime_type.startswith("image/") and len(file_bytes) <= MAX_INLINE_IMAGE_BYTES:
            attachment["image_base64"] = base64.b64encode(file_bytes).decode("utf-8")
        return attachment

    async def _handle_command(self, session_key: str, chat_id: str, text: str) -> None:
        command_text = text.split(None, 1)
        raw_command = command_text[0].strip().lower()
        args = command_text[1].strip() if len(command_text) > 1 else ""
        command = raw_command.split("@", 1)[0]
        agent = self._gateway.agent_core
        sid = self._gateway.build_virtual_sid(TELEGRAM_CHANNEL, session_key)

        if command in {"/help", "/ayuda"}:
            await self._send_session_text(
                session_key,
                self._build_help_text(),
                reply_markup=self._build_status_inline_keyboard(),
            )
            return

        if command in {"/estado", "/status"}:
            await self._send_session_text(
                session_key,
                self._build_status_text(),
                reply_markup=self._build_status_inline_keyboard(),
            )
            return

        if command in {"/start", "/resume", "/reanudar"}:
            if agent is not None:
                await agent.resume()
            await self._send_session_text(
                session_key,
                "Agente reanudado.\n\n" + self._build_help_text(),
                reply_markup=self._build_status_inline_keyboard(),
            )
            return

        if command == "/pause":
            if agent is not None:
                await agent.pause()
            await self._send_session_text(
                session_key,
                "Agente pausado.",
                reply_markup=self._build_status_inline_keyboard(),
            )
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
            await agent.approve_pending(sid)
            return

        if command in {"/cancelar", "/cancel", "/reject"}:
            if agent is None:
                await self._send_session_text(session_key, "El backend del agente no esta disponible.")
                return
            await agent.reject_pending(sid)
            return

        if command == "/modo":
            if agent is None:
                await self._send_session_text(session_key, "El backend del agente no esta disponible.")
                return
            if not args:
                await self._send_session_text(
                    session_key,
                    f"Modo actual del agente: {agent.current_mode}. Usa /modo <nombre> para cambiarlo en esta sesion.",
                )
                return
            try:
                response = await agent.set_gateway_session_mode(TELEGRAM_CHANNEL, session_key, args)
            except Exception as exc:
                await self._send_session_text(session_key, f"No pude cambiar el modo: {exc}")
                return
            await self._send_session_text(
                session_key,
                f"Modo de la sesion cambiado a {response.get('current_mode_name') or response.get('current_mode')}.",
            )
            return

        await self._send_session_text(session_key, self._build_help_text())

    async def _send_session_text(
        self,
        session_key: str,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        payload = {"reply_markup": reply_markup} if isinstance(reply_markup, dict) else None
        await self._gateway.send_text_notification(
            TELEGRAM_CHANNEL,
            session_key,
            text,
            level="info",
            source_type="gateway.telegram",
            payload=payload,
        )

    async def _send_image_notification(self, chat_id: str, item: dict[str, Any]) -> None:
        payload = item.get("payload") or {}
        image_b64 = str(payload.get("image_b64") or payload.get("photo_b64") or "").strip()
        image_path = str(payload.get("image_path") or "").strip()
        caption = str(payload.get("caption") or item.get("body") or item.get("title") or "").strip()
        reply_markup = payload.get("reply_markup") if isinstance(payload, dict) else None
        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        file_bytes: bytes | None = None
        filename = _sanitize_filename(
            str(payload.get("filename") or "gmini-screenshot.png"),
            "gmini-screenshot.png",
        )
        mime_type = str(payload.get("mime_type") or "image/png").strip() or "image/png"

        if image_b64:
            file_bytes = base64.b64decode(image_b64)
        elif image_path:
            file_bytes = Path(image_path).read_bytes()
            filename = _sanitize_filename(Path(image_path).name, filename)

        if not file_bytes:
            text = self._render_notification_text(item)
            if text:
                await self._send_raw_text(chat_id, text)
                return
            raise RuntimeError("La notificacion de imagen no tiene contenido utilizable.")

        form = aiohttp.FormData()
        form.add_field("chat_id", chat_id)
        if caption:
            form.add_field("caption", caption)
        if isinstance(reply_markup, dict):
            form.add_field("reply_markup", json.dumps(reply_markup, ensure_ascii=False))
        form.add_field(
            "photo",
            file_bytes,
            filename=filename,
            content_type=mime_type,
        )
        await self._telegram_api_form("sendPhoto", form)

    async def _send_document_notification(self, chat_id: str, item: dict[str, Any]) -> None:
        payload = item.get("payload") or {}
        file_b64 = str(payload.get("file_b64") or "").strip()
        file_path = str(payload.get("file_path") or "").strip()
        caption = str(payload.get("caption") or item.get("body") or item.get("title") or "").strip()
        reply_markup = payload.get("reply_markup") if isinstance(payload, dict) else None
        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        file_bytes: bytes | None = None
        filename = _sanitize_filename(
            str(payload.get("filename") or "gmini-document.bin"),
            "gmini-document.bin",
        )
        mime_type = str(payload.get("mime_type") or "application/octet-stream").strip() or "application/octet-stream"

        if file_b64:
            file_bytes = base64.b64decode(file_b64)
        elif file_path:
            file_bytes = Path(file_path).read_bytes()
            filename = _sanitize_filename(Path(file_path).name, filename)

        if not file_bytes:
            text = self._render_notification_text(item)
            if text:
                await self._send_raw_text(chat_id, text)
                return
            raise RuntimeError("La notificacion de documento no tiene contenido utilizable.")

        form = aiohttp.FormData()
        form.add_field("chat_id", chat_id)
        if caption:
            form.add_field("caption", caption)
        if isinstance(reply_markup, dict):
            form.add_field("reply_markup", json.dumps(reply_markup, ensure_ascii=False))
        form.add_field(
            "document",
            file_bytes,
            filename=filename,
            content_type=mime_type,
        )
        await self._telegram_api_form("sendDocument", form)

    async def _send_raw_text(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        if not self.bot_token:
            return
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if isinstance(reply_markup, dict):
            payload["reply_markup"] = reply_markup
        await self._telegram_api("sendMessage", payload)

    async def _download_file_bytes(self, remote_path: str) -> bytes:
        token = self.bot_token
        if not token:
            raise RuntimeError("Telegram bot token no configurado.")
        normalized_path = str(remote_path or "").lstrip("/")
        if not normalized_path:
            raise RuntimeError("Ruta remota de archivo vacia.")
        target_timeout = self.long_poll_timeout_seconds + 10.0
        request_timeout = aiohttp.ClientTimeout(total=target_timeout)
        url = f"{self.base_url}/file/bot{token}/{normalized_path}"
        async with aiohttp.ClientSession(timeout=request_timeout) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise RuntimeError(
                        f"Telegram file download devolvio HTTP {response.status}: {text}"
                    )
                return await response.read()

    async def _telegram_api(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        token = self.bot_token
        if not token:
            raise RuntimeError("Telegram bot token no configurado.")

        target_timeout = timeout or (self.long_poll_timeout_seconds + 5.0)
        request_timeout = aiohttp.ClientTimeout(total=target_timeout)
        url = f"{self.base_url}/bot{token}/{method}"

        async with aiohttp.ClientSession(timeout=request_timeout) as session:
            async with session.post(url, json=payload) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(
                        f"Telegram API {method} devolvio HTTP {response.status}: {data}"
                    )
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram API {method} rechazo la solicitud: {data}")
        self._last_error = ""
        return data

    async def _answer_callback_query(
        self,
        callback_query_id: str,
        *,
        text: str = "",
        show_alert: bool = False,
    ) -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:200]
        if show_alert:
            payload["show_alert"] = True
        await self._telegram_api("answerCallbackQuery", payload)

    async def _clear_message_reply_markup(self, chat_id: str, message_id: int) -> None:
        await self._telegram_api(
            "editMessageReplyMarkup",
            {
                "chat_id": chat_id,
                "message_id": int(message_id),
                "reply_markup": {"inline_keyboard": []},
            },
        )

    def _parse_callback_data(self, value: str) -> tuple[str, str]:
        raw = str(value or "").strip()
        if not raw:
            return "", ""
        prefix, separator, tail = raw.rpartition(":")
        if separator and prefix.startswith("gmini:") and tail and prefix.count(":") >= 1:
            return prefix, tail
        return raw, ""

    async def _telegram_api_form(
        self,
        method: str,
        form: aiohttp.FormData,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        token = self.bot_token
        if not token:
            raise RuntimeError("Telegram bot token no configurado.")

        target_timeout = timeout or (self.long_poll_timeout_seconds + 10.0)
        request_timeout = aiohttp.ClientTimeout(total=target_timeout)
        url = f"{self.base_url}/bot{token}/{method}"

        async with aiohttp.ClientSession(timeout=request_timeout) as session:
            async with session.post(url, data=form) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(
                        f"Telegram API {method} devolvio HTTP {response.status}: {data}"
                    )
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram API {method} rechazo la solicitud: {data}")
        self._last_error = ""
        return data

    def _build_session_key(self, chat_type: str, chat_id: str) -> str:
        if chat_type == "private":
            if self.default_chat_id and chat_id == self.default_chat_id:
                return "main"
            if len(self.allowed_chat_ids) <= 1:
                return "main"
            return f"private:{chat_id}"
        if chat_type in {"group", "supergroup"}:
            return f"group:{chat_id}"
        return f"channel:{chat_id}"

    def _build_display_name(self, chat: dict[str, Any]) -> str:
        if chat.get("title"):
            return str(chat.get("title"))
        name_parts = [
            str(chat.get("first_name") or "").strip(),
            str(chat.get("last_name") or "").strip(),
        ]
        combined = " ".join(part for part in name_parts if part).strip()
        if combined:
            return combined
        if chat.get("username"):
            return f"@{chat.get('username')}"
        return str(chat.get("id") or "Telegram")

    def _should_process_group_message(self, text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if normalized.startswith("/"):
            return True
        if self._bot_username and f"@{self._bot_username}" in normalized:
            return True
        return any(alias.lower() in normalized for alias in self.group_activation_aliases if alias)

    def _build_help_text(self) -> str:
        return (
            "Comandos disponibles:\n"
            "/estado\n"
            "/start\n"
            "/pause\n"
            "/stop\n"
            "/aprobar\n"
            "/cancelar\n"
            "/modo <nombre>\n\n"
            "Tambien puedes escribirme una tarea en lenguaje natural o enviarme una imagen/documento para usarlo como contexto."
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

    def _build_status_inline_keyboard(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "Estado", "callback_data": "gmini:status"},
                    {"text": "Pausar", "callback_data": "gmini:pause"},
                ],
                [
                    {"text": "Reanudar", "callback_data": "gmini:start"},
                    {"text": "Stop", "callback_data": "gmini:stop"},
                ],
            ]
        }

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
