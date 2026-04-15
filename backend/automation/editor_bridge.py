"""WebSocket bridge for IDE integrations such as VS Code or Cursor."""

from __future__ import annotations

import asyncio
import copy
import json
import uuid
from typing import Any

from loguru import logger
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

_bridge: EditorBridge | None = None


def _default_state() -> dict[str, Any]:
    return {
        "connected": False,
        "editor": "",
        "version": "",
        "workspaceFolders": [],
        "activeFile": None,
        "selection": None,
        "diagnostics": {
            "path": None,
            "count": 0,
            "items": [],
        },
        "timestamp": None,
    }


def get_editor_bridge() -> EditorBridge:
    """Retorna la instancia global del bridge del editor."""
    global _bridge
    if _bridge is None:
        _bridge = EditorBridge()
    return _bridge


class EditorBridge:
    def __init__(self) -> None:
        self._ws: WebSocket | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._connected = False
        self._editor_info: dict[str, Any] = {}
        self._state: dict[str, Any] = _default_state()
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    @property
    def editor_info(self) -> dict[str, Any]:
        return copy.deepcopy(self._editor_info)

    @property
    def current_state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    async def handle_websocket(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            if self._ws and self._ws.client_state == WebSocketState.CONNECTED:
                try:
                    await self._ws.close()
                except Exception:
                    pass
            self._ws = ws
            self._connected = True
            self._state["connected"] = True

        logger.info("[EditorBridge] IDE conectado")

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning(f"[EditorBridge] JSON invalido: {raw[:200]}")
                    continue

                event = msg.get("event", "")
                data = msg.get("data", {})
                await self._handle_message(event, data if isinstance(data, dict) else {})
        except WebSocketDisconnect:
            logger.info("[EditorBridge] IDE desconectado")
        except Exception as exc:
            logger.warning(f"[EditorBridge] Error en WebSocket: {exc}")
        finally:
            async with self._lock:
                self._ws = None
                self._connected = False
                self._state["connected"] = False
                for future in self._pending.values():
                    if not future.done():
                        future.set_exception(ConnectionError("Editor bridge disconnected"))
                self._pending.clear()

    async def _handle_message(self, event: str, data: dict[str, Any]) -> None:
        if event == "editor:hello":
            self._editor_info = dict(data)
            logger.info(
                "[EditorBridge] Handshake OK - editor="
                f"{self._editor_info.get('editor', '?')} version="
                f"{self._editor_info.get('version', '?')} workspaceFolders="
                f"{len(self._editor_info.get('workspaceFolders', []))}"
            )
            return

        if event == "editor:state":
            self._state = self._normalize_state(data)
            active_file = self._state.get("activeFile") or {}
            logger.debug(
                "[EditorBridge] Estado actualizado - activeFile="
                f"{str(active_file.get('path', '')).strip()}"
            )
            return

        if event == "editor:response":
            response_id = str(data.get("id", ""))
            future = self._pending.pop(response_id, None)
            if future and not future.done():
                future.set_result(data)
            else:
                logger.warning(f"[EditorBridge] Response sin pending: id={response_id}")
            return

        if event == "editor:pong":
            logger.debug("[EditorBridge] Pong recibido")
            return

        logger.debug(f"[EditorBridge] Evento desconocido: {event}")

    async def send_command(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Envia un comando a la extension del editor y espera respuesta."""
        if not self.is_connected or not self._ws:
            raise ConnectionError("Editor bridge not connected")

        request_id = uuid.uuid4().hex[:12]
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future

        payload = json.dumps(
            {
                "event": "editor:command",
                "data": {
                    "id": request_id,
                    "command": command,
                    "params": params or {},
                },
            }
        )

        try:
            await self._ws.send_text(payload)
        except Exception as exc:
            self._pending.pop(request_id, None)
            raise ConnectionError(f"Failed to send command: {exc}") from exc

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise TimeoutError(
                f"Editor command '{command}' timed out after {timeout}s"
            ) from exc

    async def get_state(self) -> dict[str, Any]:
        data = await self.send_command("state", timeout=5.0)
        state = data.get("state")
        if isinstance(state, dict):
            self._state = self._normalize_state(state)
        return data

    async def get_active_file(self) -> dict[str, Any]:
        return await self.send_command("active_file", timeout=5.0)

    async def get_selection(self) -> dict[str, Any]:
        return await self.send_command("selection", timeout=5.0)

    async def get_workspace_folders(self) -> dict[str, Any]:
        return await self.send_command("workspace_folders", timeout=5.0)

    async def get_diagnostics(self, path: str | None = None) -> dict[str, Any]:
        params = {"path": path} if path else None
        return await self.send_command("diagnostics", params=params, timeout=5.0)

    async def get_document_symbols(self, path: str | None = None) -> dict[str, Any]:
        params = {"path": path} if path else None
        return await self.send_command("document_symbols", params=params, timeout=8.0)

    async def find_symbols(
        self,
        *,
        query: str,
        path: str | None = None,
        kind: str | None = None,
        max_results: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": query,
            "path": path,
            "kind": kind,
            "max_results": max_results,
        }
        return await self.send_command("find_symbols", params=params, timeout=8.0)

    async def reveal_symbol(
        self,
        *,
        query: str,
        path: str | None = None,
        kind: str | None = None,
        occurrence: int = 1,
        preserve_focus: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": query,
            "occurrence": occurrence,
            "preserve_focus": preserve_focus,
        }
        if path:
            params["path"] = path
        if kind:
            params["kind"] = kind
        return await self.send_command("reveal_symbol", params=params, timeout=8.0)

    async def reveal_range(
        self,
        *,
        path: str,
        start_line: int = 1,
        start_column: int = 1,
        end_line: int | None = None,
        end_column: int | None = None,
        preserve_focus: bool = False,
    ) -> dict[str, Any]:
        return await self.send_command(
            "reveal_range",
            params={
                "path": path,
                "start_line": start_line,
                "start_column": start_column,
                "end_line": end_line,
                "end_column": end_column,
                "preserve_focus": preserve_focus,
            },
            timeout=8.0,
        )

    async def open_diagnostic(
        self,
        *,
        path: str | None = None,
        index: int | None = None,
        direction: str | None = None,
        preserve_focus: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "preserve_focus": preserve_focus,
        }
        if path:
            params["path"] = path
        if index is not None:
            params["index"] = index
        if direction:
            params["direction"] = direction
        return await self.send_command("open_diagnostic", params=params, timeout=8.0)

    async def apply_edit(
        self,
        *,
        path: str,
        text: str,
        start_line: int = 1,
        start_column: int = 1,
        end_line: int | None = None,
        end_column: int | None = None,
        save: bool = False,
    ) -> dict[str, Any]:
        return await self.send_command(
            "apply_edit",
            params={
                "path": path,
                "text": text,
                "start_line": start_line,
                "start_column": start_column,
                "end_line": end_line,
                "end_column": end_column,
                "save": save,
            },
            timeout=10.0,
        )

    async def apply_workspace_edits(
        self,
        *,
        edits: list[dict[str, Any]],
        save: bool = False,
    ) -> dict[str, Any]:
        return await self.send_command(
            "apply_workspace_edits",
            params={
                "edits": edits,
                "save": save,
            },
            timeout=15.0,
        )

    async def ping(self) -> bool:
        if not self.is_connected:
            return False
        try:
            await self.send_command("state", timeout=5.0)
        except Exception:
            return False
        return True

    def _normalize_state(self, data: dict[str, Any]) -> dict[str, Any]:
        state = _default_state()
        state["connected"] = bool(data.get("connected", self.is_connected))
        state["editor"] = str(
            data.get("editor") or self._editor_info.get("editor") or ""
        ).strip()
        state["version"] = str(
            data.get("version") or self._editor_info.get("version") or ""
        ).strip()

        workspace_folders = data.get("workspaceFolders", data.get("workspace_folders", []))
        state["workspaceFolders"] = workspace_folders if isinstance(workspace_folders, list) else []

        active_file = data.get("activeFile", data.get("active_file"))
        state["activeFile"] = active_file if isinstance(active_file, dict) else None

        selection = data.get("selection")
        state["selection"] = selection if isinstance(selection, dict) else None

        diagnostics = data.get("diagnostics")
        state["diagnostics"] = diagnostics if isinstance(diagnostics, dict) else _default_state()["diagnostics"]

        state["timestamp"] = data.get("timestamp", data.get("ts"))
        return state


__all__ = ["EditorBridge", "get_editor_bridge"]
