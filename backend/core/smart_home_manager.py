"""
G-Mini Agent — Smart Home Manager.
Capa de abstracción para controlar dispositivos del hogar inteligente.
Soporta Home Assistant como proveedor principal, con extensibilidad para otros.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite
from loguru import logger

from backend.config import ROOT_DIR, config

DB_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = DB_DIR / "gateway.db"


# ── Enums ─────────────────────────────────────────────────────────

class DeviceType(str, Enum):
    LIGHT = "light"
    SWITCH = "switch"
    PLUG = "plug"
    THERMOSTAT = "thermostat"
    CAMERA = "camera"
    SENSOR = "sensor"
    LOCK = "lock"
    COVER = "cover"
    FAN = "fan"
    MEDIA_PLAYER = "media_player"
    ALARM = "alarm"
    CLIMATE = "climate"
    VACUUM = "vacuum"
    OTHER = "other"


class DeviceState(str, Enum):
    ON = "on"
    OFF = "off"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


# ── Data Classes ──────────────────────────────────────────────────

@dataclass
class SmartDevice:
    device_id: str
    name: str
    device_type: str
    provider: str
    entity_id: str  # e.g., "light.sala" for Home Assistant
    state: str = DeviceState.UNKNOWN.value
    attributes: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    area: str = ""
    last_update: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SmartAutomation:
    automation_id: str
    name: str
    trigger_type: str  # "time", "state", "event"
    trigger_config: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Provider Interface ────────────────────────────────────────────

class SmartHomeProvider:
    """Interfaz base para proveedores de smart home."""

    name: str = "base"

    async def connect(self) -> bool:
        raise NotImplementedError

    async def disconnect(self) -> None:
        pass

    async def discover_devices(self) -> list[SmartDevice]:
        raise NotImplementedError

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        raise NotImplementedError

    async def set_state(self, entity_id: str, state: str, **kwargs: Any) -> bool:
        raise NotImplementedError

    async def call_service(
        self, domain: str, service: str, entity_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def get_all_states(self) -> list[dict[str, Any]]:
        raise NotImplementedError


# ── Home Assistant Provider ───────────────────────────────────────

class HomeAssistantProvider(SmartHomeProvider):
    """Proveedor Home Assistant vía HTTP API REST."""

    name = "home_assistant"

    def __init__(self) -> None:
        self._base_url = ""
        self._token = ""
        self._session: Any = None
        self._connected = False

    async def connect(self) -> bool:
        import aiohttp

        self._base_url = str(
            config.get("smart_home", "home_assistant", "url", default="http://localhost:8123")
        ).rstrip("/")
        self._token = str(
            config.get("smart_home", "home_assistant", "token", default="") or ""
        ).strip()

        if not self._token:
            from backend.security.vault import get_api_key
            self._token = get_api_key("home_assistant") or ""

        if not self._token:
            logger.warning("Home Assistant: no se encontró token de acceso")
            return False

        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        )

        try:
            async with self._session.get(f"{self._base_url}/api/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Home Assistant conectado: {data.get('message', 'OK')}")
                    self._connected = True
                    return True
                logger.warning(f"Home Assistant respondió con status {resp.status}")
                return False
        except Exception as exc:
            logger.warning(f"No se pudo conectar a Home Assistant: {exc}")
            return False

    async def disconnect(self) -> None:
        self._connected = False
        if self._session:
            await self._session.close()
            self._session = None

    async def discover_devices(self) -> list[SmartDevice]:
        if not self._connected or not self._session:
            return []
        try:
            async with self._session.get(f"{self._base_url}/api/states") as resp:
                if resp.status != 200:
                    return []
                states = await resp.json()
        except Exception as exc:
            logger.warning(f"HA discover error: {exc}")
            return []

        devices: list[SmartDevice] = []
        type_map = {
            "light": DeviceType.LIGHT,
            "switch": DeviceType.SWITCH,
            "climate": DeviceType.CLIMATE,
            "camera": DeviceType.CAMERA,
            "sensor": DeviceType.SENSOR,
            "binary_sensor": DeviceType.SENSOR,
            "lock": DeviceType.LOCK,
            "cover": DeviceType.COVER,
            "fan": DeviceType.FAN,
            "media_player": DeviceType.MEDIA_PLAYER,
            "alarm_control_panel": DeviceType.ALARM,
            "vacuum": DeviceType.VACUUM,
        }

        for entity in states:
            eid: str = entity.get("entity_id", "")
            domain = eid.split(".")[0] if "." in eid else ""
            dt = type_map.get(domain)
            if not dt:
                continue

            attrs = entity.get("attributes", {})
            friendly = attrs.get("friendly_name", eid)

            caps: list[str] = []
            if domain == "light":
                caps = ["turn_on", "turn_off"]
                if "brightness" in attrs:
                    caps.append("brightness")
                if "color_temp" in attrs or "hs_color" in attrs:
                    caps.append("color")
            elif domain in ("switch", "fan"):
                caps = ["turn_on", "turn_off"]
            elif domain == "climate":
                caps = ["set_temperature", "set_hvac_mode"]
            elif domain == "cover":
                caps = ["open", "close", "stop"]
            elif domain == "lock":
                caps = ["lock", "unlock"]
            elif domain == "media_player":
                caps = ["play", "pause", "stop", "volume"]
            elif domain == "vacuum":
                caps = ["start", "stop", "return_to_base"]

            devices.append(SmartDevice(
                device_id=eid,
                name=friendly,
                device_type=dt.value,
                provider=self.name,
                entity_id=eid,
                state=entity.get("state", "unknown"),
                attributes=attrs,
                capabilities=caps,
                area=attrs.get("area", ""),
                last_update=entity.get("last_updated", ""),
            ))

        return devices

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        if not self._connected or not self._session:
            return {"error": "No conectado"}
        try:
            async with self._session.get(
                f"{self._base_url}/api/states/{entity_id}"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"Status {resp.status}"}
        except Exception as exc:
            return {"error": str(exc)}

    async def set_state(self, entity_id: str, state: str, **kwargs: Any) -> bool:
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        service = "turn_on" if state in ("on", "true", "1") else "turn_off"
        result = await self.call_service(domain, service, entity_id, **kwargs)
        return "error" not in result

    async def call_service(
        self, domain: str, service: str, entity_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        if not self._connected or not self._session:
            return {"error": "No conectado a Home Assistant"}

        payload: dict[str, Any] = {"entity_id": entity_id}
        payload.update(kwargs)

        url = f"{self._base_url}/api/services/{domain}/{service}"
        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    return {"ok": True, "result": data}
                text = await resp.text()
                return {"error": f"Status {resp.status}: {text}"}
        except Exception as exc:
            return {"error": str(exc)}

    async def get_all_states(self) -> list[dict[str, Any]]:
        if not self._connected or not self._session:
            return []
        try:
            async with self._session.get(f"{self._base_url}/api/states") as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        except Exception:
            return []


# ── Smart Home Manager ────────────────────────────────────────────

class SmartHomeManager:
    """Orquestador central de dispositivos inteligentes."""

    def __init__(self) -> None:
        self._db_path = self._resolve_db_path()
        self._providers: dict[str, SmartHomeProvider] = {}
        self._devices: dict[str, SmartDevice] = {}
        self._automations: dict[str, SmartAutomation] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    @staticmethod
    def _resolve_db_path() -> Path:
        configured = str(config.get("smart_home", "db_path", default="") or "").strip()
        if configured:
            p = Path(configured)
            return p if p.is_absolute() else ROOT_DIR / p
        return DEFAULT_DB_PATH

    # ── Initialization ────────────────────────────────────────────

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._create_tables()

        enabled = config.get("smart_home", "enabled", default=False)
        if not enabled:
            self._initialized = True
            logger.info("SmartHomeManager: deshabilitado en configuración")
            return

        primary = str(config.get("smart_home", "primary_provider", default="home_assistant"))
        if primary == "home_assistant":
            provider = HomeAssistantProvider()
            ok = await provider.connect()
            if ok:
                self._providers["home_assistant"] = provider
                await self._discover_all()
            else:
                logger.warning("SmartHomeManager: no se pudo conectar a Home Assistant")

        await self._load_automations()
        self._initialized = True
        logger.info(
            f"SmartHomeManager inicializado — "
            f"{len(self._devices)} dispositivos, "
            f"{len(self._automations)} automatizaciones"
        )

    async def shutdown(self) -> None:
        for provider in self._providers.values():
            try:
                await provider.disconnect()
            except Exception:
                pass
        self._providers.clear()

    async def _create_tables(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS smart_home_devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    state TEXT DEFAULT 'unknown',
                    attributes_json TEXT DEFAULT '{}',
                    capabilities_json TEXT DEFAULT '[]',
                    area TEXT DEFAULT '',
                    last_update TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS smart_home_automations (
                    automation_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_config_json TEXT DEFAULT '{}',
                    actions_json TEXT DEFAULT '[]',
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT
                )
            """)
            await db.commit()

    # ── Device Discovery ──────────────────────────────────────────

    async def _discover_all(self) -> None:
        for provider in self._providers.values():
            try:
                devices = await provider.discover_devices()
                for d in devices:
                    self._devices[d.device_id] = d
                await self._persist_devices(devices)
                logger.info(f"Descubiertos {len(devices)} dispositivos de {provider.name}")
            except Exception as exc:
                logger.warning(f"Error descubriendo dispositivos de {provider.name}: {exc}")

    async def refresh_devices(self) -> int:
        self._devices.clear()
        await self._discover_all()
        return len(self._devices)

    # ── Device Control ────────────────────────────────────────────

    async def list_devices(
        self, device_type: str | None = None, area: str | None = None
    ) -> list[dict[str, Any]]:
        result = []
        for d in self._devices.values():
            if device_type and d.device_type != device_type:
                continue
            if area and d.area.lower() != area.lower():
                continue
            result.append(d.to_dict())
        return result

    async def get_device_state(self, device_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"error": f"Dispositivo '{device_id}' no encontrado"}
        provider = self._providers.get(device.provider)
        if not provider:
            return {"error": f"Proveedor '{device.provider}' no conectado"}
        state = await provider.get_state(device.entity_id)
        if "error" not in state:
            device.state = state.get("state", device.state)
            device.attributes = state.get("attributes", device.attributes)
            device.last_update = state.get("last_updated", "")
        return state

    async def control_device(
        self, device_id: str, action: str, **params: Any
    ) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"ok": False, "error": f"Dispositivo '{device_id}' no encontrado"}
        provider = self._providers.get(device.provider)
        if not provider:
            return {"ok": False, "error": f"Proveedor '{device.provider}' no conectado"}

        domain = device.entity_id.split(".")[0] if "." in device.entity_id else device.device_type
        result = await provider.call_service(domain, action, device.entity_id, **params)
        if "error" not in result:
            new_state = await provider.get_state(device.entity_id)
            if "error" not in new_state:
                device.state = new_state.get("state", device.state)
                device.attributes = new_state.get("attributes", device.attributes)
        return result

    async def set_device_state(self, device_id: str, state: str, **kwargs: Any) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"ok": False, "error": f"Dispositivo '{device_id}' no encontrado"}
        provider = self._providers.get(device.provider)
        if not provider:
            return {"ok": False, "error": f"Proveedor '{device.provider}' no conectado"}
        ok = await provider.set_state(device.entity_id, state, **kwargs)
        return {"ok": ok}

    async def get_home_summary(self) -> dict[str, Any]:
        by_type: dict[str, list[dict[str, str]]] = {}
        for d in self._devices.values():
            by_type.setdefault(d.device_type, []).append({
                "id": d.device_id,
                "name": d.name,
                "state": d.state,
                "area": d.area,
            })

        by_area: dict[str, int] = {}
        for d in self._devices.values():
            area = d.area or "Sin área"
            by_area[area] = by_area.get(area, 0) + 1

        return {
            "total_devices": len(self._devices),
            "providers": list(self._providers.keys()),
            "by_type": by_type,
            "by_area": by_area,
        }

    # ── Automations ───────────────────────────────────────────────

    async def create_automation(
        self,
        name: str,
        trigger_type: str,
        trigger_config: dict[str, Any],
        actions: list[dict[str, Any]],
    ) -> SmartAutomation:
        auto = SmartAutomation(
            automation_id=str(uuid.uuid4()),
            name=name,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            actions=actions,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._automations[auto.automation_id] = auto
        await self._persist_automation(auto)
        logger.info(f"Automatización creada: '{name}' (trigger={trigger_type})")
        return auto

    async def list_automations(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._automations.values()]

    async def delete_automation(self, automation_id: str) -> bool:
        auto = self._automations.pop(automation_id, None)
        if not auto:
            return False
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM smart_home_automations WHERE automation_id = ?",
                (automation_id,),
            )
            await db.commit()
        return True

    async def toggle_automation(self, automation_id: str, enabled: bool) -> bool:
        auto = self._automations.get(automation_id)
        if not auto:
            return False
        auto.enabled = enabled
        await self._persist_automation(auto)
        return True

    async def execute_automation(self, automation_id: str) -> dict[str, Any]:
        auto = self._automations.get(automation_id)
        if not auto:
            return {"ok": False, "error": "Automatización no encontrada"}
        results = []
        for action in auto.actions:
            device_id = action.get("device_id", "")
            act = action.get("action", "")
            params = action.get("params", {})
            r = await self.control_device(device_id, act, **params)
            results.append({"device_id": device_id, "action": act, "result": r})
        return {"ok": True, "results": results}

    # ── Persistence ───────────────────────────────────────────────

    async def _persist_devices(self, devices: list[SmartDevice]) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            for d in devices:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO smart_home_devices
                    (device_id, name, device_type, provider, entity_id, state,
                     attributes_json, capabilities_json, area, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.device_id, d.name, d.device_type, d.provider,
                        d.entity_id, d.state,
                        json.dumps(d.attributes), json.dumps(d.capabilities),
                        d.area, d.last_update,
                    ),
                )
            await db.commit()

    async def _persist_automation(self, auto: SmartAutomation) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO smart_home_automations
                (automation_id, name, trigger_type, trigger_config_json,
                 actions_json, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    auto.automation_id, auto.name, auto.trigger_type,
                    json.dumps(auto.trigger_config), json.dumps(auto.actions),
                    1 if auto.enabled else 0, auto.created_at,
                ),
            )
            await db.commit()

    async def _load_automations(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM smart_home_automations")
            rows = await cursor.fetchall()
        for row in rows:
            auto = SmartAutomation(
                automation_id=row["automation_id"],
                name=row["name"],
                trigger_type=row["trigger_type"],
                trigger_config=json.loads(row["trigger_config_json"] or "{}"),
                actions=json.loads(row["actions_json"] or "[]"),
                enabled=bool(row["enabled"]),
                created_at=row["created_at"] or "",
            )
            self._automations[auto.automation_id] = auto


# ── Singleton ─────────────────────────────────────────────────────

_smart_home: SmartHomeManager | None = None


def get_smart_home() -> SmartHomeManager:
    global _smart_home
    if _smart_home is None:
        _smart_home = SmartHomeManager()
    return _smart_home
