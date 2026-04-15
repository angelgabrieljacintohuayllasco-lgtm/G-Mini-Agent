"""
Macro Recorder and RPA Workflow Engine.

Records user actions as workflows, converts them to replayable macros,
supports parameterization and trigger-based execution.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


class MacroStatus(str, Enum):
    RECORDING = "recording"
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"


class TriggerType(str, Enum):
    MANUAL = "manual"
    CRON = "cron"
    EVENT = "event"
    COMMAND = "command"
    HOTKEY = "hotkey"


@dataclass
class MacroStep:
    step_id: str
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)
    delay_ms: int = 0
    description: str = ""
    order: int = 0


@dataclass
class Macro:
    macro_id: str
    name: str
    description: str
    steps: list[MacroStep]
    status: str = "draft"
    trigger_type: str = "manual"
    trigger_value: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    run_count: int = 0
    last_run: float | None = None
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "macro_id": self.macro_id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {"step_id": s.step_id, "action_type": s.action_type,
                 "params": s.params, "delay_ms": s.delay_ms,
                 "description": s.description, "order": s.order}
                for s in self.steps
            ],
            "status": self.status,
            "trigger_type": self.trigger_type,
            "trigger_value": self.trigger_value,
            "variables": self.variables,
            "tags": self.tags,
            "run_count": self.run_count,
            "last_run": self.last_run,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MacroEngine:
    """Records, stores, and replays macros."""

    def __init__(self) -> None:
        db_path = config.get("macros", "db_path") or "data/macros.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._recording: dict[str, list[MacroStep]] = {}  # session_id -> steps
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS macros (
                    macro_id      TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    description   TEXT NOT NULL DEFAULT '',
                    steps_json    TEXT NOT NULL DEFAULT '[]',
                    status        TEXT NOT NULL DEFAULT 'draft',
                    trigger_type  TEXT NOT NULL DEFAULT 'manual',
                    trigger_value TEXT NOT NULL DEFAULT '',
                    variables     TEXT NOT NULL DEFAULT '{}',
                    tags          TEXT NOT NULL DEFAULT '[]',
                    run_count     INTEGER NOT NULL DEFAULT 0,
                    last_run      REAL,
                    created_at    REAL NOT NULL,
                    updated_at    REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS macro_runs (
                    run_id      TEXT PRIMARY KEY,
                    macro_id    TEXT NOT NULL,
                    started_at  REAL NOT NULL,
                    finished_at REAL,
                    status      TEXT NOT NULL DEFAULT 'running',
                    result      TEXT NOT NULL DEFAULT '',
                    steps_executed INTEGER NOT NULL DEFAULT 0,
                    error       TEXT,
                    FOREIGN KEY (macro_id) REFERENCES macros(macro_id)
                )
            """)
            conn.commit()

    # ── Recording ────────────────────────────────────────────────────

    def start_recording(self, session_id: str) -> str:
        macro_id = str(uuid.uuid4())[:12]
        self._recording[session_id] = []
        logger.info(f"Macro recording started: session={session_id}")
        return macro_id

    def record_step(
        self,
        session_id: str,
        action_type: str,
        params: dict[str, Any],
        delay_ms: int = 0,
        description: str = "",
    ) -> bool:
        if session_id not in self._recording:
            return False
        steps = self._recording[session_id]
        step = MacroStep(
            step_id=str(uuid.uuid4())[:8],
            action_type=action_type,
            params=params,
            delay_ms=delay_ms,
            description=description,
            order=len(steps),
        )
        steps.append(step)
        return True

    def stop_recording(
        self,
        session_id: str,
        name: str = "",
        description: str = "",
    ) -> Macro | None:
        steps = self._recording.pop(session_id, None)
        if not steps:
            return None

        now = time.time()
        macro = Macro(
            macro_id=str(uuid.uuid4())[:12],
            name=name or f"Macro {time.strftime('%Y-%m-%d %H:%M')}",
            description=description,
            steps=steps,
            status=MacroStatus.DRAFT.value,
            created_at=now,
            updated_at=now,
        )
        self._save_macro(macro)
        logger.info(f"Macro recorded: {macro.macro_id} with {len(steps)} steps")
        return macro

    # ── CRUD ─────────────────────────────────────────────────────────

    def _save_macro(self, macro: Macro) -> None:
        steps_json = json.dumps([
            {"step_id": s.step_id, "action_type": s.action_type,
             "params": s.params, "delay_ms": s.delay_ms,
             "description": s.description, "order": s.order}
            for s in macro.steps
        ])
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO macros
                (macro_id, name, description, steps_json, status, trigger_type, trigger_value,
                 variables, tags, run_count, last_run, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (macro.macro_id, macro.name, macro.description, steps_json,
                 macro.status, macro.trigger_type, macro.trigger_value,
                 json.dumps(macro.variables), json.dumps(macro.tags),
                 macro.run_count, macro.last_run, macro.created_at, macro.updated_at),
            )
            conn.commit()

    def get_macro(self, macro_id: str) -> Macro | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM macros WHERE macro_id = ?", (macro_id,)).fetchone()
            if not row:
                return None
            return self._row_to_macro(row)

    def list_macros(self, status: str | None = None, limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    "SELECT * FROM macros WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM macros ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [self._row_to_macro(r).to_dict() for r in rows]

    def delete_macro(self, macro_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM macro_runs WHERE macro_id = ?", (macro_id,))
            cur = conn.execute("DELETE FROM macros WHERE macro_id = ?", (macro_id,))
            conn.commit()
            return cur.rowcount > 0

    def update_macro(self, macro_id: str, updates: dict) -> bool:
        macro = self.get_macro(macro_id)
        if not macro:
            return False
        if "name" in updates:
            macro.name = updates["name"]
        if "description" in updates:
            macro.description = updates["description"]
        if "trigger_type" in updates:
            macro.trigger_type = updates["trigger_type"]
        if "trigger_value" in updates:
            macro.trigger_value = updates["trigger_value"]
        if "variables" in updates:
            macro.variables = updates["variables"]
        if "status" in updates:
            macro.status = updates["status"]
        if "tags" in updates:
            macro.tags = updates["tags"]
        macro.updated_at = time.time()
        self._save_macro(macro)
        return True

    def _row_to_macro(self, row: Any) -> Macro:
        steps_data = json.loads(row["steps_json"])
        steps = [
            MacroStep(
                step_id=s["step_id"], action_type=s["action_type"],
                params=s.get("params", {}), delay_ms=s.get("delay_ms", 0),
                description=s.get("description", ""), order=s.get("order", 0),
            )
            for s in steps_data
        ]
        return Macro(
            macro_id=row["macro_id"], name=row["name"],
            description=row["description"], steps=steps,
            status=row["status"], trigger_type=row["trigger_type"],
            trigger_value=row["trigger_value"],
            variables=json.loads(row["variables"]),
            tags=json.loads(row["tags"]),
            run_count=row["run_count"], last_run=row["last_run"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    # ── Execution ────────────────────────────────────────────────────

    async def execute_macro(
        self,
        macro_id: str,
        variables: dict[str, Any] | None = None,
    ) -> dict:
        """Execute a macro by replaying its steps."""
        macro = self.get_macro(macro_id)
        if not macro:
            return {"error": "Macro not found"}
        if macro.status not in (MacroStatus.READY.value, MacroStatus.DRAFT.value):
            return {"error": f"Macro status is {macro.status}, cannot run"}

        run_id = str(uuid.uuid4())[:12]
        now = time.time()

        # Log run start
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO macro_runs (run_id, macro_id, started_at, status) VALUES (?, ?, ?, 'running')",
                (run_id, macro_id, now),
            )
            conn.commit()

        # Merge variables
        merged_vars = {**macro.variables, **(variables or {})}
        steps_executed = 0
        error = None
        results = []

        for step in sorted(macro.steps, key=lambda s: s.order):
            try:
                # Apply variable substitution
                params = self._substitute_vars(step.params, merged_vars)
                results.append({
                    "step_id": step.step_id,
                    "action_type": step.action_type,
                    "params": params,
                    "status": "executed",
                })
                steps_executed += 1
            except Exception as e:
                error = f"Step {step.step_id} failed: {e}"
                results.append({
                    "step_id": step.step_id,
                    "action_type": step.action_type,
                    "status": "failed",
                    "error": str(e),
                })
                break

        # Update run record
        status = "completed" if error is None else "failed"
        finished_at = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE macro_runs SET finished_at = ?, status = ?, steps_executed = ?, error = ? WHERE run_id = ?",
                (finished_at, status, steps_executed, error, run_id),
            )
            conn.execute(
                "UPDATE macros SET run_count = run_count + 1, last_run = ? WHERE macro_id = ?",
                (finished_at, macro_id),
            )
            conn.commit()

        return {
            "run_id": run_id,
            "macro_id": macro_id,
            "status": status,
            "steps_executed": steps_executed,
            "total_steps": len(macro.steps),
            "duration_ms": (finished_at - now) * 1000,
            "results": results,
            "error": error,
        }

    @staticmethod
    def _substitute_vars(params: dict, variables: dict) -> dict:
        """Replace {{var_name}} placeholders in params."""
        result = {}
        for k, v in params.items():
            if isinstance(v, str):
                for var_name, var_val in variables.items():
                    v = v.replace(f"{{{{{var_name}}}}}", str(var_val))
            result[k] = v
        return result

    def get_runs(self, macro_id: str, limit: int = 20) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM macro_runs WHERE macro_id = ? ORDER BY started_at DESC LIMIT ?",
                (macro_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Import/Export ────────────────────────────────────────────────

    def export_macro(self, macro_id: str) -> str | None:
        macro = self.get_macro(macro_id)
        if not macro:
            return None
        return json.dumps(macro.to_dict(), indent=2, ensure_ascii=False)

    def import_macro(self, data: dict) -> Macro:
        now = time.time()
        steps = [
            MacroStep(
                step_id=s.get("step_id", str(uuid.uuid4())[:8]),
                action_type=s["action_type"],
                params=s.get("params", {}),
                delay_ms=s.get("delay_ms", 0),
                description=s.get("description", ""),
                order=s.get("order", 0),
            )
            for s in data.get("steps", [])
        ]
        macro = Macro(
            macro_id=str(uuid.uuid4())[:12],
            name=data.get("name", "Imported macro"),
            description=data.get("description", ""),
            steps=steps,
            status=MacroStatus.DRAFT.value,
            trigger_type=data.get("trigger_type", "manual"),
            trigger_value=data.get("trigger_value", ""),
            variables=data.get("variables", {}),
            tags=data.get("tags", []),
            created_at=now,
            updated_at=now,
        )
        self._save_macro(macro)
        return macro


# ── Singleton ────────────────────────────────────────────────────────────

_macro_engine: MacroEngine | None = None


def get_macro_engine() -> MacroEngine:
    global _macro_engine
    if _macro_engine is None:
        _macro_engine = MacroEngine()
    return _macro_engine
