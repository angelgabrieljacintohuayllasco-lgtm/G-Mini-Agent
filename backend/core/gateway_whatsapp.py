"""
G-Mini Agent - Conector WhatsApp Web para GatewayService.
Usa un bridge Node por stdio para enviar/recibir mensajes de WhatsApp Web.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from backend.config import ROOT_DIR, config

if TYPE_CHECKING:
    from backend.core.gateway_service import GatewayService


WHATSAPP_CHANNEL = "whatsapp"
DEFAULT_NODE_EXECUTABLE = "node"
DEFAULT_BRIDGE_WORKDIR = ROOT_DIR / "assets" / "whatsapp-bridge"
DEFAULT_BRIDGE_SCRIPT = DEFAULT_BRIDGE_WORKDIR / "bridge.js"
WHATSAPP_INBOX_DIR = ROOT_DIR / "data" / "gateway" / "whatsapp" / "inbox"
MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = value.strip()
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


class WhatsAppGatewayConnector:
    def __init__(self, gateway: "GatewayService"):
        self._gateway = gateway
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._watcher_task: asyncio.Task | None = None
        self._request_counter = 0
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._ready = False
        self._last_error: str = ""
        self._last_qr: str = ""
        self._last_status: str = "stopped"
        self._stop_requested = False

    @property
    def _channel_config(self) -> dict[str, Any]:
        raw = config.get("gateway", "channels", WHATSAPP_CHANNEL, default={}) or {}
        return raw if isinstance(raw, dict) else {}

    @property
    def enabled(self) -> bool:
        return self._gateway.channel_enabled(WHATSAPP_CHANNEL)

    @property
    def node_executable(self) -> str:
        return str(self._channel_config.get("node_executable") or DEFAULT_NODE_EXECUTABLE).strip() or DEFAULT_NODE_EXECUTABLE

    @property
    def bridge_workdir(self) -> Path:
        configured = str(self._channel_config.get("bridge_workdir") or "").strip()
        target = Path(configured) if configured else DEFAULT_BRIDGE_WORKDIR
        if not target.is_absolute():
            target = ROOT_DIR / target
        return target

    @property
    def bridge_script(self) -> Path:
        configured = str(self._channel_config.get("bridge_script_path") or "").strip()
        target = Path(configured) if configured else DEFAULT_BRIDGE_SCRIPT
        if not target.is_absolute():
            target = ROOT_DIR / target
        return target

    @property
    def session_name(self) -> str:
        return str(self._channel_config.get("session_name") or "default").strip() or "default"

    @property
    def default_chat_id(self) -> str:
        return str(self._channel_config.get("default_chat_id") or "").strip()

    @property
    def allowed_chat_ids(self) -> list[str]:
        return _coerce_list(self._channel_config.get("allowed_chat_ids", []))

    @property
    def startup_timeout_seconds(self) -> float:
        return _coerce_float(self._channel_config.get("startup_timeout_seconds"), 45.0)

    @property
    def inbox_dir(self) -> Path:
        WHATSAPP_INBOX_DIR.mkdir(parents=True, exist_ok=True)
        return WHATSAPP_INBOX_DIR

    @property
    def group_activation_aliases(self) -> list[str]:
        aliases = _coerce_list(self._channel_config.get("group_activation_aliases", []))
        return aliases or ["g-mini", "gmini", "agente"]

    @property
    def ready(self) -> bool:
        return self._ready and self.running

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    def get_status_detail(self) -> str:
        if not self.enabled:
            return "Canal deshabilitado."
        if not shutil.which(self.node_executable):
            return f"No se encontro Node.js en PATH ({self.node_executable})."
        if not self.bridge_script.exists():
            return f"No existe el bridge de WhatsApp: {self.bridge_script}"
        if self.ready:
            return "Bridge WhatsApp operativo."
        if self._last_qr:
            return "Bridge WhatsApp esperando escaneo QR."
        if self.running:
            return f"Bridge WhatsApp iniciado ({self._last_status})."
        if self._last_error:
            return f"Bridge WhatsApp detenido por error reciente: {self._last_error}"
        return "Bridge WhatsApp configurado pero inactivo."

    async def start(self) -> None:
        if not self.enabled or self.running:
            return
        if not shutil.which(self.node_executable):
            self._last_error = f"Node.js no encontrado: {self.node_executable}"
            self._last_status = "error"
            await self._gateway.set_state_value(
                "whatsapp_runtime",
                {
                    "status": "error",
                    "error": self._last_error,
                    "session_name": self.session_name,
                },
            )
            return
        if not self.bridge_script.exists():
            self._last_error = f"Bridge no encontrado: {self.bridge_script}"
            self._last_status = "error"
            await self._gateway.set_state_value(
                "whatsapp_runtime",
                {
                    "status": "error",
                    "error": self._last_error,
                    "session_name": self.session_name,
                },
            )
            return

        self._stop_requested = False
        self._ready = False
        self._last_error = ""
        self._last_qr = ""
        self._last_status = "starting"
        await self._gateway.set_state_value(
            "whatsapp_runtime",
            {
                "status": "starting",
                "session_name": self.session_name,
            },
        )
        env = {**os.environ, "GMINI_WHATSAPP_SESSION": self.session_name}
        self._process = await asyncio.create_subprocess_exec(
            self.node_executable,
            str(self.bridge_script),
            cwd=str(self.bridge_workdir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._reader_task = asyncio.create_task(self._read_stdout_loop(), name="gateway-whatsapp-stdout")
        self._stderr_task = asyncio.create_task(self._read_stderr_loop(), name="gateway-whatsapp-stderr")
        self._watcher_task = asyncio.create_task(self._watch_process(), name="gateway-whatsapp-watch")
        logger.info("Gateway WhatsApp bridge iniciado")

    async def stop(self) -> None:
        self._stop_requested = True
        process = self._process
        self._ready = False
        self._last_qr = ""
        self._last_status = "stopped"

        if process and process.returncode is None:
            try:
                await self._send_command({"command": "shutdown"}, expect_response=False)
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except Exception:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except Exception:
                    process.kill()

        self._process = None

        for task in (self._reader_task, self._stderr_task, self._watcher_task):
            if task:
                task.cancel()
        self._reader_task = None
        self._stderr_task = None
        self._watcher_task = None

        pending = list(self._pending_requests.values())
        self._pending_requests.clear()
        for future in pending:
            if not future.done():
                future.set_exception(RuntimeError("Bridge WhatsApp detenido."))
        await self._gateway.set_state_value(
            "whatsapp_runtime",
            {
                "status": "stopped",
                "session_name": self.session_name,
            },
        )
        logger.info("Gateway WhatsApp bridge detenido")

    async def send_notification(self, item: dict[str, Any]) -> None:
        chat_id = self.resolve_chat_id(str(item.get("session_key") or ""))
        if not chat_id:
            raise RuntimeError("No se pudo resolver el chat_id de WhatsApp para la notificacion.")
        payload = item.get("payload") or {}
        render = str(payload.get("render") or "").strip().lower()
        if render == "image":
            await self._send_media_notification(chat_id, item, media_kind="image")
            return
        if render in {"file", "document"}:
            await self._send_media_notification(chat_id, item, media_kind="document")
            return
        text = str(payload.get("text") or "").strip()
        if not text:
            text = self._render_notification_text(item)
        if not text:
            raise RuntimeError("La notificacion de WhatsApp no tiene texto para enviar.")
        await self._send_command(
            {
                "command": "send_text",
                "chat_id": chat_id,
                "text": text,
            }
        )

    async def _send_media_notification(
        self,
        chat_id: str,
        item: dict[str, Any],
        *,
        media_kind: str,
    ) -> None:
        payload = item.get("payload") or {}
        caption = str(payload.get("caption") or item.get("body") or item.get("title") or "").strip()
        if media_kind == "image":
            data_b64 = str(payload.get("image_b64") or payload.get("photo_b64") or "").strip()
            file_path = str(payload.get("image_path") or "").strip()
            default_name = "gmini-image.png"
            default_mime = "image/png"
        else:
            data_b64 = str(payload.get("file_b64") or "").strip()
            file_path = str(payload.get("file_path") or "").strip()
            default_name = "gmini-document.bin"
            default_mime = "application/octet-stream"

        filename = _sanitize_filename(
            str(payload.get("filename") or Path(file_path).name or default_name),
            default_name,
        )
        mime_type = str(payload.get("mime_type") or default_mime).strip() or default_mime

        if not data_b64 and not file_path:
            text = self._render_notification_text(item)
            if text:
                await self._send_command(
                    {
                        "command": "send_text",
                        "chat_id": chat_id,
                        "text": text,
                    }
                )
                return
            raise RuntimeError("La notificacion multimedia de WhatsApp no tiene contenido utilizable.")

        await self._send_command(
            {
                "command": "send_media",
                "chat_id": chat_id,
                "media_kind": media_kind,
                "mime_type": mime_type,
                "filename": filename,
                "data_base64": data_b64,
                "file_path": file_path,
                "caption": caption,
            }
        )

    def resolve_chat_id(self, session_key: str) -> str:
        normalized = str(session_key or "").strip()
        if not normalized or normalized == "main":
            return self.default_chat_id
        if ":" in normalized:
            _, chat_id = normalized.rsplit(":", 1)
            return str(chat_id or "").strip()
        return normalized

    async def _send_command(
        self,
        payload: dict[str, Any],
        *,
        expect_response: bool = True,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if not self.running or not self._process or not self._process.stdin:
            raise RuntimeError("Bridge WhatsApp no esta operativo.")

        request_id = ""
        future: asyncio.Future | None = None
        if expect_response:
            self._request_counter += 1
            request_id = f"req_{self._request_counter}"
            payload = dict(payload)
            payload["request_id"] = request_id
            future = asyncio.get_running_loop().create_future()
            self._pending_requests[request_id] = future

        line = json.dumps(payload, ensure_ascii=False) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()

        if not expect_response or future is None:
            return {"ok": True}

        try:
            result = await asyncio.wait_for(future, timeout=timeout or self.startup_timeout_seconds)
        finally:
            self._pending_requests.pop(request_id, None)
        if not isinstance(result, dict):
            raise RuntimeError("Respuesta invalida del bridge WhatsApp.")
        if not result.get("success", False):
            raise RuntimeError(str(result.get("error") or "Bridge WhatsApp rechazo la solicitud."))
        return result

    async def _read_stdout_loop(self) -> None:
        if not self._process or not self._process.stdout:
            return
        try:
            while True:
                raw_line = await self._process.stdout.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"WhatsApp bridge emitio JSON invalido: {line[:200]}")
                    continue
                await self._handle_bridge_event(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
            logger.warning(f"Fallo leyendo stdout de WhatsApp bridge: {exc}")

    async def _read_stderr_loop(self) -> None:
        if not self._process or not self._process.stderr:
            return
        try:
            while True:
                raw_line = await self._process.stderr.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line:
                    logger.info(f"[WhatsAppBridge] {line}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(f"Fallo leyendo stderr de WhatsApp bridge: {exc}")

    async def _watch_process(self) -> None:
        process = self._process
        if not process:
            return
        try:
            return_code = await process.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
            self._last_status = "error"
            await self._gateway.set_state_value(
                "whatsapp_runtime",
                {
                    "status": "error",
                    "error": self._last_error,
                    "session_name": self.session_name,
                },
            )
            return

        if self._process is process:
            self._process = None
        self._ready = False
        self._last_qr = ""

        if self._stop_requested:
            return

        self._last_status = "exited"
        self._last_error = (
            f"Bridge WhatsApp finalizo con codigo {return_code}."
            if return_code not in (None, 0)
            else "Bridge WhatsApp finalizo."
        )
        await self._gateway.set_state_value(
            "whatsapp_runtime",
            {
                "status": "error" if return_code not in (None, 0) else "stopped",
                "error": self._last_error,
                "session_name": self.session_name,
                "return_code": return_code,
            },
        )

        pending = list(self._pending_requests.values())
        self._pending_requests.clear()
        for future in pending:
            if not future.done():
                future.set_exception(RuntimeError(self._last_error))

    async def _handle_bridge_event(self, payload: dict[str, Any]) -> None:
        event = str(payload.get("event") or "").strip().lower()
        if event == "response":
            request_id = str(payload.get("request_id") or "").strip()
            future = self._pending_requests.get(request_id)
            if future and not future.done():
                future.set_result(payload)
            return

        if event == "qr":
            self._last_qr = str(payload.get("qr") or "").strip()
            self._last_status = "qr"
            self._last_error = ""
            await self._gateway.set_state_value(
                "whatsapp_runtime",
                {
                    "status": "qr",
                    "qr": self._last_qr,
                    "qr_data_url": str(payload.get("qr_data_url") or "").strip(),
                    "session_name": self.session_name,
                },
            )
            return

        if event == "ready":
            self._ready = True
            self._last_qr = ""
            self._last_status = "ready"
            self._last_error = ""
            await self._gateway.set_state_value(
                "whatsapp_runtime",
                {
                    "status": "ready",
                    "session_name": self.session_name,
                    "info": payload.get("info") or {},
                },
            )
            return

        if event == "status":
            self._last_status = str(payload.get("status") or "").strip() or self._last_status
            if payload.get("error"):
                self._last_error = str(payload.get("error") or "").strip()
            if str(payload.get("status") or "").strip().lower() not in {"ready", "connected"}:
                self._ready = False
            await self._gateway.set_state_value("whatsapp_runtime", payload)
            return

        if event == "message":
            await self._handle_incoming_message(payload)
            return

    async def _handle_incoming_message(self, payload: dict[str, Any]) -> None:
        chat_id = str(payload.get("chat_id") or "").strip()
        text = str(payload.get("text") or "").strip()
        attachments = self._normalize_attachments(payload.get("attachments"))
        if not chat_id or (not text and not attachments):
            return
        if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
            logger.info(f"WhatsApp chat no autorizado ignorado: {chat_id}")
            return

        chat_type = str(payload.get("chat_type") or "private").strip().lower()
        session_key = self._build_session_key(chat_type, chat_id)
        display_name = str(payload.get("display_name") or payload.get("push_name") or chat_id).strip() or chat_id
        await self._gateway.register_remote_session(
            WHATSAPP_CHANNEL,
            session_key=session_key,
            display_name=display_name,
            meta={
                "chat_id": chat_id,
                "chat_type": chat_type,
                "push_name": str(payload.get("push_name") or ""),
                "author": str(payload.get("author") or ""),
            },
        )

        if chat_type != "private" and not self._should_process_group_message(text):
            return

        if self._gateway.agent_core is None:
            return
        if text.startswith("/"):
            await self._handle_command(session_key, chat_id, text)
            return
        await self._gateway.agent_core.process_gateway_message(
            WHATSAPP_CHANNEL,
            session_key,
            text,
            attachments=attachments,
        )

    async def _handle_command(self, session_key: str, chat_id: str, text: str) -> None:
        command_text = text.split(None, 1)
        raw_command = command_text[0].strip().lower()
        args = command_text[1].strip() if len(command_text) > 1 else ""
        command = raw_command.split("@", 1)[0]
        agent = self._gateway.agent_core
        sid = self._gateway.build_virtual_sid(WHATSAPP_CHANNEL, session_key)

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
            await agent.approve_pending(sid, token=args or None)
            return

        if command in {"/cancelar", "/cancel", "/reject"}:
            if agent is None:
                await self._send_session_text(session_key, "El backend del agente no esta disponible.")
                return
            await agent.reject_pending(sid, token=args or None)
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
                response = await agent.set_gateway_session_mode(WHATSAPP_CHANNEL, session_key, args)
            except Exception as exc:
                await self._send_session_text(session_key, f"No pude cambiar el modo: {exc}")
                return
            await self._send_session_text(
                session_key,
                f"Modo de la sesion cambiado a {response.get('current_mode_name') or response.get('current_mode')}.",
            )
            return

        await self._send_session_text(session_key, self._build_help_text())

    async def _send_session_text(self, session_key: str, text: str) -> None:
        await self._gateway.send_text_notification(
            WHATSAPP_CHANNEL,
            session_key,
            text,
            level="info",
            source_type="gateway.whatsapp",
        )

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

    def _should_process_group_message(self, text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if normalized.startswith("/"):
            return True
        return any(alias.lower() in normalized for alias in self.group_activation_aliases if alias)

    def _normalize_attachments(self, raw_attachments: Any) -> list[dict[str, Any]]:
        attachments: list[dict[str, Any]] = []
        if not isinstance(raw_attachments, list):
            return attachments

        for index, item in enumerate(raw_attachments, start=1):
            if not isinstance(item, dict):
                continue

            mime_type = str(item.get("mime_type") or "application/octet-stream").strip() or "application/octet-stream"
            kind = str(item.get("kind") or "").strip().lower()
            if kind not in {"image", "file", "document", "audio", "video"}:
                if mime_type.startswith("image/"):
                    kind = "image"
                elif mime_type.startswith("audio/"):
                    kind = "audio"
                elif mime_type.startswith("video/"):
                    kind = "video"
                elif mime_type == "application/pdf":
                    kind = "document"
                else:
                    kind = "file"
            base_name = str(item.get("file_name") or item.get("filename") or "").strip()
            fallback_name = f"whatsapp_attachment_{index}"
            suffix = ""
            if "." not in base_name:
                guessed = mime_type.split("/", 1)[-1].replace("jpeg", "jpg")
                if guessed and guessed != mime_type:
                    suffix = f".{guessed}"
            safe_name = _sanitize_filename(base_name or f"{fallback_name}{suffix}", f"{fallback_name}{suffix or '.bin'}")

            file_bytes: bytes | None = None
            data_b64 = str(item.get("data_base64") or item.get("base64") or "").strip()
            if data_b64:
                try:
                    file_bytes = base64.b64decode(data_b64)
                except Exception:
                    file_bytes = None

            local_path = str(item.get("local_path") or "").strip()
            if not local_path and file_bytes is not None:
                target = self.inbox_dir / safe_name
                counter = 1
                while target.exists():
                    target = self.inbox_dir / f"{target.stem}_{counter}{target.suffix}"
                    counter += 1
                target.write_bytes(file_bytes)
                local_path = str(target)

            if not local_path and not file_bytes:
                continue

            attachment = {
                "kind": kind,
                "source": WHATSAPP_CHANNEL,
                "file_name": Path(local_path).name if local_path else safe_name,
                "mime_type": mime_type,
                "caption": str(item.get("caption") or "").strip(),
            }
            if local_path:
                attachment["local_path"] = local_path
            if file_bytes is not None:
                attachment["size_bytes"] = len(file_bytes)
            if mime_type.startswith("image/") and file_bytes is not None and len(file_bytes) <= MAX_INLINE_IMAGE_BYTES:
                attachment["image_base64"] = base64.b64encode(file_bytes).decode("utf-8")
            attachments.append(attachment)

        return attachments

    def _build_session_key(self, chat_type: str, chat_id: str) -> str:
        if chat_type == "private":
            if self.default_chat_id and chat_id == self.default_chat_id:
                return "main"
            if len(self.allowed_chat_ids) <= 1:
                return "main"
            return f"private:{chat_id}"
        return f"group:{chat_id}"

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
