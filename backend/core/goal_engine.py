"""
Goal Engine — Persistent objectives with KPI tracking,
auto-decomposition into DAG tasks, and replanification on deviation.
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


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNING = "replanning"


class KPIType(str, Enum):
    NUMERIC = "numeric"          # target_value reached
    BOOLEAN = "boolean"          # done or not
    PERCENTAGE = "percentage"    # 0-100
    THRESHOLD = "threshold"     # must stay above/below


@dataclass
class KPI:
    kpi_id: str
    name: str
    kpi_type: str
    target_value: float
    current_value: float = 0.0
    unit: str = ""

    def progress_pct(self) -> float:
        if self.kpi_type == KPIType.BOOLEAN.value:
            return 100.0 if self.current_value >= 1 else 0.0
        if self.target_value == 0:
            return 100.0
        return min(100.0, (self.current_value / self.target_value) * 100)

    def to_dict(self) -> dict:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "kpi_type": self.kpi_type,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "progress_pct": round(self.progress_pct(), 1),
        }


@dataclass
class SubTask:
    task_id: str
    title: str
    status: str = "pending"    # pending / running / completed / failed
    dag_id: str | None = None  # linked DAG if auto-decomposed
    created_at: float = 0.0
    completed_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "dag_id": self.dag_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Goal:
    goal_id: str
    title: str
    description: str
    deadline: float | None = None
    status: str = "active"
    kpis: list[KPI] = field(default_factory=list)
    sub_tasks: list[SubTask] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: float | None = None
    replan_count: int = 0

    def overall_progress(self) -> float:
        if not self.kpis:
            if not self.sub_tasks:
                return 0.0
            done = sum(1 for t in self.sub_tasks if t.status == "completed")
            return (done / len(self.sub_tasks)) * 100
        return sum(k.progress_pct() for k in self.kpis) / len(self.kpis)

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline,
            "status": self.status,
            "kpis": [k.to_dict() for k in self.kpis],
            "sub_tasks": [t.to_dict() for t in self.sub_tasks],
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "progress_pct": round(self.overall_progress(), 1),
            "replan_count": self.replan_count,
        }


class GoalEngine:
    """Manages persistent objectives with KPIs, sub-tasks, and replanification."""

    def __init__(self) -> None:
        db_path = config.get("goals", "db_path") or "data/goals.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    goal_id       TEXT PRIMARY KEY,
                    title         TEXT NOT NULL,
                    description   TEXT NOT NULL DEFAULT '',
                    deadline      REAL,
                    status        TEXT NOT NULL DEFAULT 'active',
                    kpis_json     TEXT NOT NULL DEFAULT '[]',
                    tasks_json    TEXT NOT NULL DEFAULT '[]',
                    tags_json     TEXT NOT NULL DEFAULT '[]',
                    created_at    REAL NOT NULL,
                    updated_at    REAL NOT NULL,
                    completed_at  REAL,
                    replan_count  INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)")
            conn.commit()

    # ── CRUD ─────────────────────────────────────────────────────────

    def create_goal(
        self,
        title: str,
        description: str = "",
        deadline: float | None = None,
        kpis: list[dict] | None = None,
        sub_tasks: list[dict] | None = None,
        tags: list[str] | None = None,
    ) -> Goal:
        now = time.time()
        goal_id = str(uuid.uuid4())[:12]

        kpi_objs = []
        for k in (kpis or []):
            kpi_objs.append(KPI(
                kpi_id=k.get("kpi_id", str(uuid.uuid4())[:8]),
                name=k["name"],
                kpi_type=k.get("kpi_type", "numeric"),
                target_value=k.get("target_value", 1.0),
                current_value=k.get("current_value", 0.0),
                unit=k.get("unit", ""),
            ))

        task_objs = []
        for t in (sub_tasks or []):
            task_objs.append(SubTask(
                task_id=t.get("task_id", str(uuid.uuid4())[:8]),
                title=t["title"],
                status=t.get("status", "pending"),
                dag_id=t.get("dag_id"),
                created_at=now,
            ))

        goal = Goal(
            goal_id=goal_id, title=title, description=description,
            deadline=deadline, kpis=kpi_objs, sub_tasks=task_objs,
            tags=tags or [], created_at=now, updated_at=now,
        )

        self._save_goal(goal)
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM goals WHERE goal_id = ?", (goal_id,)).fetchone()
            if not row:
                return None
            return self._row_to_goal(row)

    def list_goals(
        self,
        status: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM goals"
            params: list[Any] = []
            conditions = []
            if status:
                conditions.append("status = ?")
                params.append(status)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()

        goals = [self._row_to_goal(r).to_dict() for r in rows]
        if tag:
            goals = [g for g in goals if tag in g.get("tags", [])]
        return goals

    def delete_goal(self, goal_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute("DELETE FROM goals WHERE goal_id = ?", (goal_id,))
            conn.commit()
            return cur.rowcount > 0

    # ── KPI management ───────────────────────────────────────────────

    def update_kpi(self, goal_id: str, kpi_id: str, value: float) -> Goal | None:
        goal = self.get_goal(goal_id)
        if not goal:
            return None
        for kpi in goal.kpis:
            if kpi.kpi_id == kpi_id:
                kpi.current_value = value
                break
        goal.updated_at = time.time()

        # Check if goal is now complete
        if goal.overall_progress() >= 100.0:
            goal.status = GoalStatus.COMPLETED.value
            goal.completed_at = time.time()

        self._save_goal(goal)
        return goal

    # ── Sub-task management ──────────────────────────────────────────

    def add_sub_task(self, goal_id: str, title: str, dag_id: str | None = None) -> Goal | None:
        goal = self.get_goal(goal_id)
        if not goal:
            return None
        task = SubTask(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            dag_id=dag_id,
            created_at=time.time(),
        )
        goal.sub_tasks.append(task)
        goal.updated_at = time.time()
        self._save_goal(goal)
        return goal

    def update_sub_task(self, goal_id: str, task_id: str, status: str) -> Goal | None:
        goal = self.get_goal(goal_id)
        if not goal:
            return None
        for task in goal.sub_tasks:
            if task.task_id == task_id:
                task.status = status
                if status == "completed":
                    task.completed_at = time.time()
                break
        goal.updated_at = time.time()
        self._save_goal(goal)
        return goal

    # ── Replanification ──────────────────────────────────────────────

    def check_deviation(self, goal_id: str) -> dict | None:
        """Check if a goal is behind schedule and needs replanning."""
        goal = self.get_goal(goal_id)
        if not goal or goal.status != GoalStatus.ACTIVE.value:
            return None

        progress = goal.overall_progress()
        result: dict[str, Any] = {
            "goal_id": goal_id,
            "progress_pct": round(progress, 1),
            "needs_replan": False,
            "reason": None,
        }

        # Check deadline proximity
        if goal.deadline:
            now = time.time()
            total_duration = goal.deadline - goal.created_at
            elapsed = now - goal.created_at
            if total_duration > 0:
                expected_progress = (elapsed / total_duration) * 100
                if progress < expected_progress * 0.7:  # 30% behind expected
                    result["needs_replan"] = True
                    result["reason"] = f"Behind schedule: {progress:.0f}% actual vs {expected_progress:.0f}% expected"
                    result["expected_pct"] = round(expected_progress, 1)

        # Check for too many failed sub-tasks
        if goal.sub_tasks:
            failed = sum(1 for t in goal.sub_tasks if t.status == "failed")
            if failed > len(goal.sub_tasks) * 0.3:
                result["needs_replan"] = True
                result["reason"] = (result.get("reason", "") or "") + f" High failure rate: {failed}/{len(goal.sub_tasks)}"

        return result

    def trigger_replan(self, goal_id: str) -> Goal | None:
        """Mark a goal for replanning — resets failed sub-tasks."""
        goal = self.get_goal(goal_id)
        if not goal:
            return None
        goal.status = GoalStatus.REPLANNING.value
        goal.replan_count += 1
        # Reset failed tasks to pending
        for task in goal.sub_tasks:
            if task.status == "failed":
                task.status = "pending"
                task.completed_at = None
        goal.updated_at = time.time()
        self._save_goal(goal)
        return goal

    def activate_goal(self, goal_id: str) -> Goal | None:
        goal = self.get_goal(goal_id)
        if not goal:
            return None
        goal.status = GoalStatus.ACTIVE.value
        goal.updated_at = time.time()
        self._save_goal(goal)
        return goal

    # ── Persistence helpers ──────────────────────────────────────────

    def _save_goal(self, goal: Goal) -> None:
        kpis_json = json.dumps([k.to_dict() for k in goal.kpis])
        tasks_json = json.dumps([t.to_dict() for t in goal.sub_tasks])
        tags_json = json.dumps(goal.tags)
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO goals
                (goal_id, title, description, deadline, status, kpis_json,
                 tasks_json, tags_json, created_at, updated_at, completed_at, replan_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (goal.goal_id, goal.title, goal.description, goal.deadline,
                 goal.status, kpis_json, tasks_json, tags_json,
                 goal.created_at, goal.updated_at, goal.completed_at, goal.replan_count),
            )
            conn.commit()

    def _row_to_goal(self, row: sqlite3.Row) -> Goal:
        kpis_data = json.loads(row["kpis_json"])
        tasks_data = json.loads(row["tasks_json"])
        tags = json.loads(row["tags_json"])

        kpis = [KPI(
            kpi_id=k["kpi_id"], name=k["name"], kpi_type=k["kpi_type"],
            target_value=k["target_value"], current_value=k["current_value"],
            unit=k.get("unit", ""),
        ) for k in kpis_data]

        tasks = [SubTask(
            task_id=t["task_id"], title=t["title"], status=t["status"],
            dag_id=t.get("dag_id"), created_at=t.get("created_at", 0),
            completed_at=t.get("completed_at"),
        ) for t in tasks_data]

        return Goal(
            goal_id=row["goal_id"], title=row["title"],
            description=row["description"], deadline=row["deadline"],
            status=row["status"], kpis=kpis, sub_tasks=tasks,
            tags=tags, created_at=row["created_at"],
            updated_at=row["updated_at"], completed_at=row["completed_at"],
            replan_count=row["replan_count"],
        )


# ── Singleton ────────────────────────────────────────────────────────────

_engine: GoalEngine | None = None


def get_goal_engine() -> GoalEngine:
    global _engine
    if _engine is None:
        _engine = GoalEngine()
    return _engine
