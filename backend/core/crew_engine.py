"""
CrewEngine — Multi-agent crew orchestration for G-Mini Agent (Phase 2).

Manages crew definitions (roles + tasks) with sequential and hierarchical
execution processes, using the existing SubAgentOrchestrator for worker spawning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from loguru import logger

from backend.config import config
from backend.core.cost_tracker import BudgetLimitExceeded


@dataclass
class AgentRole:
    """A specialized role within a crew."""
    role: str
    goal: str = ""
    backstory: str = ""
    model: str | None = None
    provider: str | None = None
    tools: list[str] = field(default_factory=list)
    can_delegate: bool = False
    max_iterations: int = 10


@dataclass
class CrewTask:
    """A unit of work assigned to a specific role in the crew."""
    id: str = field(default_factory=lambda: f"task_{uuid4().hex[:8]}")
    description: str = ""
    expected_output: str = ""
    agent_role: str = ""
    context_from: list[str] = field(default_factory=list)
    async_execution: bool = False
    status: str = "pending"
    output: str = ""
    error: str = ""


@dataclass
class CrewDefinition:
    """Full crew definition with roles and metadata."""
    id: str = ""
    name: str = ""
    process: str = "sequential"       # "sequential" | "hierarchical"
    manager_model: str | None = None   # Only for hierarchical
    agents: list[AgentRole] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "process": self.process,
            "manager_model": self.manager_model,
            "agents": [
                {
                    "role": a.role,
                    "goal": a.goal,
                    "backstory": a.backstory,
                    "model": a.model,
                    "provider": a.provider,
                    "tools": a.tools,
                    "can_delegate": a.can_delegate,
                    "max_iterations": a.max_iterations,
                }
                for a in self.agents
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrewDefinition:
        agents = []
        for a in data.get("agents", []):
            if isinstance(a, dict):
                agents.append(AgentRole(
                    role=a.get("role", ""),
                    goal=a.get("goal", ""),
                    backstory=a.get("backstory", ""),
                    model=a.get("model"),
                    provider=a.get("provider"),
                    tools=a.get("tools", []),
                    can_delegate=bool(a.get("can_delegate", False)),
                    max_iterations=int(a.get("max_iterations", 10)),
                ))
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            process=data.get("process", "sequential"),
            manager_model=data.get("manager_model"),
            agents=agents,
        )


@dataclass
class CrewRun:
    """State of a crew execution run."""
    run_id: str = field(default_factory=lambda: f"crew_run_{uuid4().hex[:8]}")
    crew_id: str = ""
    crew_name: str = ""
    process: str = "sequential"
    status: str = "pending"  # pending | running | completed | failed
    tasks: list[CrewTask] = field(default_factory=list)
    final_output: str = ""
    error: str = ""
    started_at: str = ""
    finished_at: str = ""
    total_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "crew_id": self.crew_id,
            "crew_name": self.crew_name,
            "process": self.process,
            "status": self.status,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "expected_output": t.expected_output,
                    "agent_role": t.agent_role,
                    "status": t.status,
                    "output": t.output[:500] if t.output else "",
                    "error": t.error,
                }
                for t in self.tasks
            ],
            "final_output": self.final_output[:1000] if self.final_output else "",
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }


class CrewEngine:
    """Orchestrates multi-agent crews using the SubAgentOrchestrator."""

    def __init__(self) -> None:
        self._definitions: dict[str, CrewDefinition] = {}
        self._runs: dict[str, CrewRun] = {}
        self._load_definitions()

    def _load_definitions(self) -> None:
        """Load crew definitions from config."""
        raw = config.get("crews", "definitions", default=[])
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("id"):
                    defn = CrewDefinition.from_dict(item)
                    self._definitions[defn.id] = defn

    def _persist_definitions(self) -> None:
        """Save definitions back to config."""
        defs_list = [d.to_dict() for d in self._definitions.values()]
        config.set("crews", "definitions", value=defs_list)

    # ── CRUD ───────────────────────────────────────────────────

    def list_crews(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values()]

    def get_crew(self, crew_id: str) -> CrewDefinition | None:
        return self._definitions.get(crew_id)

    def create_crew(self, data: dict[str, Any]) -> CrewDefinition:
        defn = CrewDefinition.from_dict(data)
        if not defn.id:
            defn.id = defn.name.lower().replace(" ", "-").replace(
                "/", "-"
            )[:40] or f"crew_{uuid4().hex[:6]}"
        self._definitions[defn.id] = defn
        self._persist_definitions()
        logger.info(f"Crew created: {defn.id} ({defn.name}) with {len(defn.agents)} roles")
        return defn

    def update_crew(self, crew_id: str, data: dict[str, Any]) -> CrewDefinition | None:
        if crew_id not in self._definitions:
            return None
        data["id"] = crew_id
        defn = CrewDefinition.from_dict(data)
        self._definitions[crew_id] = defn
        self._persist_definitions()
        return defn

    def delete_crew(self, crew_id: str) -> bool:
        if crew_id not in self._definitions:
            return False
        del self._definitions[crew_id]
        self._persist_definitions()
        return True

    # ── Execution ──────────────────────────────────────────────

    async def run_crew(
        self,
        crew_id: str,
        tasks: list[dict[str, str]],
        *,
        router: Any,
        subagent_orchestrator: Any,
        session_id: str = "",
        parent_mode_key: str = "normal",
        parent_task_limit_usd: float = 0.0,
        on_update: Any = None,
        planner: Any = None,
    ) -> CrewRun:
        """Execute a crew with the given tasks."""
        defn = self._definitions.get(crew_id)
        if not defn:
            raise ValueError(f"Crew not found: {crew_id}")

        run = CrewRun(
            crew_id=crew_id,
            crew_name=defn.name,
            process=defn.process,
            started_at=datetime.utcnow().isoformat(),
        )

        # Build CrewTasks from input
        for t in tasks:
            ct = CrewTask(
                description=t.get("description", ""),
                expected_output=t.get("expected_output", ""),
                agent_role=t.get("agent_role", ""),
                context_from=t.get("context_from", []),
            )
            run.tasks.append(ct)

        self._runs[run.run_id] = run
        run.status = "running"

        try:
            if defn.process == "hierarchical":
                await self._run_hierarchical(defn, run, router=router,
                    subagent_orchestrator=subagent_orchestrator,
                    session_id=session_id, parent_mode_key=parent_mode_key,
                    parent_task_limit_usd=parent_task_limit_usd,
                    on_update=on_update, planner=planner)
            else:
                await self._run_sequential(defn, run, router=router,
                    subagent_orchestrator=subagent_orchestrator,
                    session_id=session_id, parent_mode_key=parent_mode_key,
                    parent_task_limit_usd=parent_task_limit_usd,
                    on_update=on_update, planner=planner)

            run.status = "completed"
            # Build final output from all task outputs
            run.final_output = "\n\n---\n\n".join(
                f"**{t.agent_role or 'Task'}**: {t.output}" for t in run.tasks if t.output
            )
        except BudgetLimitExceeded as e:
            run.status = "failed"
            run.error = f"Budget exceeded: {e}"
        except Exception as e:
            run.status = "failed"
            run.error = str(e)
            logger.error(f"Crew run failed: {crew_id} — {e}")

        run.finished_at = datetime.utcnow().isoformat()
        return run

    async def _run_sequential(
        self,
        defn: CrewDefinition,
        run: CrewRun,
        **kwargs: Any,
    ) -> None:
        """Execute tasks sequentially, passing each output to the next."""
        router = kwargs["router"]
        subagent_orchestrator = kwargs["subagent_orchestrator"]
        session_id = kwargs.get("session_id", "")
        parent_mode_key = kwargs.get("parent_mode_key", "normal")
        parent_task_limit_usd = kwargs.get("parent_task_limit_usd", 0.0)
        on_update = kwargs.get("on_update")
        planner = kwargs.get("planner")

        previous_output = ""
        task_outputs: dict[str, str] = {}

        for task in run.tasks:
            task.status = "running"

            # Find the agent role for this task
            role = self._find_role(defn, task.agent_role)

            # Build context from previous task outputs
            context_parts = []
            if previous_output:
                context_parts.append(f"Resultado de la tarea anterior:\n{previous_output}")
            for ref_id in task.context_from:
                if ref_id in task_outputs:
                    context_parts.append(f"Contexto de {ref_id}:\n{task_outputs[ref_id]}")

            full_task = task.description
            if task.expected_output:
                full_task += f"\n\nOutput esperado: {task.expected_output}"
            if context_parts:
                full_task += "\n\n" + "\n\n".join(context_parts)

            try:
                result = await subagent_orchestrator.spawn(
                    router=router,
                    task=full_task,
                    mode_key=parent_mode_key,
                    parent_mode_key=parent_mode_key,
                    session_id=session_id,
                    parent_task_limit_usd=parent_task_limit_usd,
                    name=f"crew:{defn.name}:{role.role if role else 'worker'}",
                    model_override=role.model if role else None,
                    provider_override=role.provider if role else None,
                    can_execute=True,
                    max_iterations=role.max_iterations if role else 10,
                    on_update=on_update,
                    planner=planner,
                )
                task.output = result.get("result", "")
                task.status = "completed"
                run.total_cost_usd += result.get("total_cost_usd", 0.0)
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                raise

            previous_output = task.output
            task_outputs[task.id] = task.output

    async def _run_hierarchical(
        self,
        defn: CrewDefinition,
        run: CrewRun,
        **kwargs: Any,
    ) -> None:
        """Manager agent delegates tasks to role-specific workers."""
        router = kwargs["router"]
        subagent_orchestrator = kwargs["subagent_orchestrator"]
        session_id = kwargs.get("session_id", "")
        parent_mode_key = kwargs.get("parent_mode_key", "normal")
        parent_task_limit_usd = kwargs.get("parent_task_limit_usd", 0.0)
        on_update = kwargs.get("on_update")
        planner = kwargs.get("planner")

        # Build manager prompt with all tasks and available roles
        roles_desc = "\n".join(
            f"- {a.role}: {a.goal}" for a in defn.agents
        )
        tasks_desc = "\n".join(
            f"- Tarea {i+1}: {t.description} (output esperado: {t.expected_output or 'libre'})"
            for i, t in enumerate(run.tasks)
        )

        manager_task = (
            f"Eres el manager de un equipo multi-agente llamado '{defn.name}'.\n\n"
            f"Roles disponibles:\n{roles_desc}\n\n"
            f"Tareas a completar:\n{tasks_desc}\n\n"
            "Ejecuta cada tarea delegando al rol más apropiado. "
            "Para cada tarea, indica el resultado final. "
            "Al terminar todas, consolida un resumen ejecutivo."
        )

        # Parse manager_model
        manager_model = None
        manager_provider = None
        if defn.manager_model and ":" in defn.manager_model:
            manager_provider, manager_model = defn.manager_model.split(":", 1)

        try:
            result = await subagent_orchestrator.spawn(
                router=router,
                task=manager_task,
                mode_key=parent_mode_key,
                parent_mode_key=parent_mode_key,
                session_id=session_id,
                parent_task_limit_usd=parent_task_limit_usd,
                name=f"crew:{defn.name}:manager",
                model_override=manager_model,
                provider_override=manager_provider,
                can_execute=True,
                max_iterations=15,
                on_update=on_update,
                planner=planner,
            )
            manager_output = result.get("result", "")
            run.total_cost_usd += result.get("total_cost_usd", 0.0)

            # Distribute manager output across tasks
            for task in run.tasks:
                task.output = manager_output
                task.status = "completed"
        except Exception as e:
            for task in run.tasks:
                task.status = "failed"
                task.error = str(e)
            raise

    def _find_role(self, defn: CrewDefinition, role_name: str) -> AgentRole | None:
        """Find an agent role by name (case-insensitive prefix match)."""
        if not role_name:
            return defn.agents[0] if defn.agents else None
        role_lower = role_name.lower()
        for agent in defn.agents:
            if agent.role.lower() == role_lower or agent.role.lower().startswith(role_lower):
                return agent
        return defn.agents[0] if defn.agents else None

    # ── Runs state ─────────────────────────────────────────────

    def get_run(self, run_id: str) -> CrewRun | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._runs.values()]


# ── Module singleton ───────────────────────────────────────────

_crew_engine: CrewEngine | None = None


def get_crew_engine() -> CrewEngine:
    global _crew_engine
    if _crew_engine is None:
        _crew_engine = CrewEngine()
    return _crew_engine
