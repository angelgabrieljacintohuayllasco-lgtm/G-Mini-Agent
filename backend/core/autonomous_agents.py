"""
Autonomous Agent Framework — Specialized sub-agents for vertical domains.

Includes: Negotiation Agent, SOP Generator, Agent Arbiter,
A/B Testing Engine, What-If Simulator, Virtual CFO.
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


# ═══════════════════════════════════════════════════════════════════════
# Base agent framework
# ═══════════════════════════════════════════════════════════════════════

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    title: str
    params: dict[str, Any]
    status: str = "idle"
    result: dict[str, Any] | None = None
    error: str | None = None
    log: list[str] = field(default_factory=list)
    created_at: float = 0.0
    finished_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "title": self.title,
            "params": self.params,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "log": self.log[-20:],  # last 20 entries
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


class AutonomousAgentManager:
    """Manages autonomous sub-agents and their tasks."""

    def __init__(self) -> None:
        db_path = config.get("agents", "db_path") or "data/agents.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id     TEXT PRIMARY KEY,
                    agent_type  TEXT NOT NULL,
                    title       TEXT NOT NULL,
                    params_json TEXT NOT NULL DEFAULT '{}',
                    status      TEXT NOT NULL DEFAULT 'idle',
                    result_json TEXT,
                    error       TEXT,
                    log_json    TEXT NOT NULL DEFAULT '[]',
                    created_at  REAL NOT NULL,
                    finished_at REAL
                );

                CREATE INDEX IF NOT EXISTS idx_at_type ON agent_tasks(agent_type);
                CREATE INDEX IF NOT EXISTS idx_at_status ON agent_tasks(status);
            """)
            conn.commit()

    # ── Task management ──────────────────────────────────────────────

    def create_task(
        self,
        agent_type: str,
        title: str,
        params: dict | None = None,
    ) -> AgentTask:
        task = AgentTask(
            task_id=str(uuid.uuid4())[:12],
            agent_type=agent_type,
            title=title,
            params=params or {},
            created_at=time.time(),
        )
        self._save_task(task)
        return task

    def get_task(self, task_id: str) -> AgentTask | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM agent_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def list_tasks(
        self,
        agent_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        query = "SELECT * FROM agent_tasks"
        params: list[Any] = []
        conditions = []
        if agent_type:
            conditions.append("agent_type = ?")
            params.append(agent_type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_task(r).to_dict() for r in rows]

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> AgentTask | None:
        task = self.get_task(task_id)
        if not task:
            return None
        task.status = status
        if result:
            task.result = result
        if error:
            task.error = error
        if status in (AgentStatus.COMPLETED.value, AgentStatus.FAILED.value, AgentStatus.ESCALATED.value):
            task.finished_at = time.time()
        self._save_task(task)
        return task

    def add_log(self, task_id: str, message: str) -> None:
        task = self.get_task(task_id)
        if task:
            task.log.append(f"[{time.strftime('%H:%M:%S')}] {message}")
            self._save_task(task)

    def delete_task(self, task_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("DELETE FROM agent_tasks WHERE task_id = ?", (task_id,)).rowcount
            conn.commit()
            return c > 0

    # ── Agent type registry ──────────────────────────────────────────

    def get_available_agents(self) -> list[dict]:
        return [
            {"type": "negotiator", "name": "Agente de Negociación", "description": "Negocia precios, contratos y renovaciones de SaaS"},
            {"type": "sop_generator", "name": "Generador SOP", "description": "Detecta tareas repetidas y genera documentación viva"},
            {"type": "arbiter", "name": "Árbitro de Conflictos", "description": "Resuelve conflictos de recursos entre sub-agentes"},
            {"type": "ab_testing", "name": "A/B Testing", "description": "Experimenta con configuraciones y adopta la ganadora"},
            {"type": "what_if", "name": "Simulador What-If", "description": "Simula escenarios de negocio (pricing, contratación, churn)"},
            {"type": "cfo", "name": "CFO Virtual", "description": "P&L en tiempo real, flujo de caja, runway, proyecciones"},
        ]

    # ── Persistence helpers ──────────────────────────────────────────

    def _save_task(self, task: AgentTask) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_tasks
                (task_id, agent_type, title, params_json, status,
                 result_json, error, log_json, created_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.task_id, task.agent_type, task.title,
                 json.dumps(task.params), task.status,
                 json.dumps(task.result) if task.result else None,
                 task.error, json.dumps(task.log),
                 task.created_at, task.finished_at),
            )
            conn.commit()

    def _row_to_task(self, row: sqlite3.Row) -> AgentTask:
        return AgentTask(
            task_id=row["task_id"],
            agent_type=row["agent_type"],
            title=row["title"],
            params=json.loads(row["params_json"]),
            status=row["status"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
            log=json.loads(row["log_json"]),
            created_at=row["created_at"],
            finished_at=row["finished_at"],
        )


# ═══════════════════════════════════════════════════════════════════════
# SOP Generator
# ═══════════════════════════════════════════════════════════════════════

class SOPGenerator:
    """Detects repeated tasks and generates Standard Operating Procedures."""

    def __init__(self) -> None:
        db_path = config.get("agents", "db_path") or "data/agents.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sops (
                    sop_id      TEXT PRIMARY KEY,
                    title       TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    format      TEXT NOT NULL DEFAULT 'markdown',
                    task_pattern TEXT NOT NULL DEFAULT '',
                    executions  INTEGER NOT NULL DEFAULT 0,
                    avg_duration REAL NOT NULL DEFAULT 0,
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL
                )
            """)
            conn.commit()

    def create_sop(
        self,
        title: str,
        content: str,
        task_pattern: str = "",
        sop_format: str = "markdown",
    ) -> dict:
        sop_id = str(uuid.uuid4())[:10]
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO sops (sop_id, title, content, format, task_pattern, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sop_id, title, content, sop_format, task_pattern, now, now),
            )
            conn.commit()
        return {"sop_id": sop_id, "title": title, "format": sop_format}

    def get_sop(self, sop_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM sops WHERE sop_id = ?", (sop_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def list_sops(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT sop_id, title, format, task_pattern, executions, avg_duration, updated_at FROM sops ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_sop(self, sop_id: str, content: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute(
                "UPDATE sops SET content = ?, updated_at = ? WHERE sop_id = ?",
                (content, time.time(), sop_id),
            ).rowcount
            conn.commit()
            return c > 0

    def delete_sop(self, sop_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            c = conn.execute("DELETE FROM sops WHERE sop_id = ?", (sop_id,)).rowcount
            conn.commit()
            return c > 0


# ═══════════════════════════════════════════════════════════════════════
# A/B Testing Engine
# ═══════════════════════════════════════════════════════════════════════

class ABTestEngine:
    """Runs experiments on agent configurations."""

    def __init__(self) -> None:
        db_path = config.get("agents", "db_path") or "data/agents.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    element       TEXT NOT NULL,
                    control_json  TEXT NOT NULL,
                    variant_json  TEXT NOT NULL,
                    metric        TEXT NOT NULL,
                    status        TEXT NOT NULL DEFAULT 'running',
                    control_results TEXT NOT NULL DEFAULT '[]',
                    variant_results TEXT NOT NULL DEFAULT '[]',
                    winner        TEXT,
                    confidence    REAL,
                    created_at    REAL NOT NULL,
                    finished_at   REAL
                )
            """)
            conn.commit()

    def create_experiment(
        self,
        name: str,
        element: str,
        control: dict,
        variant: dict,
        metric: str,
    ) -> dict:
        exp_id = str(uuid.uuid4())[:10]
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO ab_experiments
                (experiment_id, name, element, control_json, variant_json, metric, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (exp_id, name, element, json.dumps(control),
                 json.dumps(variant), metric, now),
            )
            conn.commit()
        return {"experiment_id": exp_id, "name": name, "status": "running"}

    def record_result(self, experiment_id: str, group: str, value: float) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM ab_experiments WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
            if not row:
                return False

            col = "control_results" if group == "control" else "variant_results"
            results = json.loads(row[col])
            results.append(value)

            conn.execute(
                f"UPDATE ab_experiments SET {col} = ? WHERE experiment_id = ?",
                (json.dumps(results), experiment_id),
            )
            conn.commit()
        return True

    def get_experiment(self, experiment_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM ab_experiments WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["control_json"] = json.loads(d["control_json"])
            d["variant_json"] = json.loads(d["variant_json"])
            d["control_results"] = json.loads(d["control_results"])
            d["variant_results"] = json.loads(d["variant_results"])
            return d

    def list_experiments(self, status: str | None = None, limit: int = 50) -> list[dict]:
        query = "SELECT experiment_id, name, element, metric, status, winner, confidence, created_at FROM ab_experiments"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def evaluate_experiment(self, experiment_id: str) -> dict | None:
        """Evaluate if experiment has reached statistical significance."""
        exp = self.get_experiment(experiment_id)
        if not exp:
            return None

        ctrl = exp["control_results"]
        var = exp["variant_results"]

        if len(ctrl) < 10 or len(var) < 10:
            return {"status": "insufficient_data", "control_n": len(ctrl), "variant_n": len(var)}

        ctrl_mean = sum(ctrl) / len(ctrl)
        var_mean = sum(var) / len(var)

        # Simple significance test (effect size)
        diff = var_mean - ctrl_mean
        pooled = (sum((x - ctrl_mean) ** 2 for x in ctrl) + sum((x - var_mean) ** 2 for x in var))
        pooled_std = (pooled / (len(ctrl) + len(var) - 2)) ** 0.5 if len(ctrl) + len(var) > 2 else 1

        effect_size = abs(diff / pooled_std) if pooled_std > 0 else 0
        confidence = min(0.99, effect_size / 2)  # simplified

        winner = None
        if confidence >= 0.95:
            winner = "variant" if var_mean > ctrl_mean else "control"
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    "UPDATE ab_experiments SET status = 'completed', winner = ?, confidence = ?, finished_at = ? WHERE experiment_id = ?",
                    (winner, confidence, time.time(), experiment_id),
                )
                conn.commit()

        return {
            "control_mean": round(ctrl_mean, 4),
            "variant_mean": round(var_mean, 4),
            "effect_size": round(effect_size, 4),
            "confidence": round(confidence, 4),
            "winner": winner,
            "significant": confidence >= 0.95,
        }


# ═══════════════════════════════════════════════════════════════════════
# What-If Simulator
# ═══════════════════════════════════════════════════════════════════════

class WhatIfSimulator:
    """Runs scenario simulations without modifying real data."""

    def __init__(self) -> None:
        db_path = config.get("agents", "db_path") or "data/agents.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    sim_id      TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    sim_type    TEXT NOT NULL,
                    params_json TEXT NOT NULL DEFAULT '{}',
                    results_json TEXT,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    created_at  REAL NOT NULL,
                    finished_at REAL
                )
            """)
            conn.commit()

    def create_simulation(
        self,
        name: str,
        sim_type: str,
        params: dict,
    ) -> dict:
        sim_id = str(uuid.uuid4())[:10]
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO simulations (sim_id, name, sim_type, params_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (sim_id, name, sim_type, json.dumps(params), now),
            )
            conn.commit()
        return {"sim_id": sim_id, "name": name, "sim_type": sim_type, "status": "pending"}

    def run_simulation(self, sim_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM simulations WHERE sim_id = ?", (sim_id,)).fetchone()
            if not row:
                return None

        params = json.loads(row["params_json"])
        sim_type = row["sim_type"]

        # Run simulation based on type
        if sim_type == "pricing":
            results = self._sim_pricing(params)
        elif sim_type == "hiring":
            results = self._sim_hiring(params)
        elif sim_type == "churn":
            results = self._sim_churn(params)
        else:
            results = {"optimistic": params, "base": params, "pessimistic": params}

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE simulations SET results_json = ?, status = 'completed', finished_at = ? WHERE sim_id = ?",
                (json.dumps(results), time.time(), sim_id),
            )
            conn.commit()

        return {"sim_id": sim_id, "status": "completed", "results": results}

    def get_simulation(self, sim_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM simulations WHERE sim_id = ?", (sim_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["params_json"] = json.loads(d["params_json"])
            if d["results_json"]:
                d["results_json"] = json.loads(d["results_json"])
            return d

    def list_simulations(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT sim_id, name, sim_type, status, created_at, finished_at FROM simulations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Built-in simulation models ───────────────────────────────────

    def _sim_pricing(self, params: dict) -> dict:
        base_price = params.get("current_price", 100)
        change_pct = params.get("change_pct", 10)
        elasticity = params.get("elasticity", -1.5)
        current_units = params.get("current_units", 1000)

        scenarios = {}
        for label, mult in [("optimistic", 0.5), ("base", 1.0), ("pessimistic", 1.5)]:
            pct = change_pct * mult
            new_price = base_price * (1 + pct / 100)
            demand_change = elasticity * pct
            new_units = current_units * (1 + demand_change / 100)
            old_revenue = base_price * current_units
            new_revenue = new_price * new_units
            scenarios[label] = {
                "new_price": round(new_price, 2),
                "projected_units": round(new_units),
                "old_revenue": round(old_revenue, 2),
                "projected_revenue": round(new_revenue, 2),
                "revenue_change_pct": round((new_revenue - old_revenue) / old_revenue * 100, 1),
            }
        return scenarios

    def _sim_hiring(self, params: dict) -> dict:
        salary = params.get("salary", 50000)
        ramp_months = params.get("ramp_months", 3)
        productivity_gain = params.get("monthly_value_at_full", 8000)
        months = params.get("projection_months", 12)

        scenarios = {}
        for label, eff_mult in [("optimistic", 1.2), ("base", 1.0), ("pessimistic", 0.7)]:
            total_cost = salary
            total_value = 0
            for m in range(1, months + 1):
                eff = min(1.0, m / ramp_months) * eff_mult
                total_value += productivity_gain * eff
            scenarios[label] = {
                "total_cost": round(total_cost, 2),
                "total_value": round(total_value, 2),
                "roi_pct": round((total_value - total_cost) / total_cost * 100, 1),
                "breakeven_month": max(1, round(total_cost / (productivity_gain * eff_mult))),
            }
        return scenarios

    def _sim_churn(self, params: dict) -> dict:
        current_users = params.get("current_users", 10000)
        monthly_churn = params.get("monthly_churn_pct", 5)
        monthly_growth = params.get("monthly_growth", 500)
        months = params.get("projection_months", 12)

        scenarios = {}
        for label, churn_mult in [("optimistic", 0.5), ("base", 1.0), ("pessimistic", 1.5)]:
            users = current_users
            churn = monthly_churn * churn_mult
            projection = []
            for m in range(1, months + 1):
                lost = int(users * churn / 100)
                users = users - lost + monthly_growth
                projection.append({"month": m, "users": max(0, int(users)), "churned": lost})
            scenarios[label] = {
                "final_users": projection[-1]["users"],
                "total_churned": sum(p["churned"] for p in projection),
                "net_change": projection[-1]["users"] - current_users,
            }
        return scenarios


# ═══════════════════════════════════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════════════════════════════════

_mgr: AutonomousAgentManager | None = None
_sop: SOPGenerator | None = None
_ab: ABTestEngine | None = None
_whatif: WhatIfSimulator | None = None


def get_agent_manager() -> AutonomousAgentManager:
    global _mgr
    if _mgr is None:
        _mgr = AutonomousAgentManager()
    return _mgr


def get_sop_generator() -> SOPGenerator:
    global _sop
    if _sop is None:
        _sop = SOPGenerator()
    return _sop


def get_ab_engine() -> ABTestEngine:
    global _ab
    if _ab is None:
        _ab = ABTestEngine()
    return _ab


def get_whatif() -> WhatIfSimulator:
    global _whatif
    if _whatif is None:
        _whatif = WhatIfSimulator()
    return _whatif
