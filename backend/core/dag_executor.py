"""
DAG Planner — Directed Acyclic Graph task execution engine.

Supports: parallel branches, retries with backoff, checkpoints,
skip/optional branches, visualization state, and resumption after failure.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger

from backend.config import config


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class DAGNode:
    node_id: str
    name: str
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: str | None = None
    retries: int = 0
    max_retries: int = 3
    backoff_seconds: float = 1.0
    optional: bool = False
    started_at: float | None = None
    finished_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "action_type": self.action_type,
            "params": self.params,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "retries": self.retries,
            "optional": self.optional,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class DAG:
    dag_id: str
    name: str
    description: str
    nodes: dict[str, DAGNode]
    status: str = "pending"
    created_at: float = 0.0
    started_at: float | None = None
    finished_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "dag_id": self.dag_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class DAGExecutor:
    """Executes DAGs with parallel branches and retry logic."""

    def __init__(self) -> None:
        db_path = config.get("dag", "db_path") or "data/dag.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._action_handlers: dict[str, Callable] = {}
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dags (
                    dag_id      TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    nodes_json  TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    created_at  REAL NOT NULL,
                    started_at  REAL,
                    finished_at REAL
                )
            """)
            conn.commit()

    def register_handler(self, action_type: str, handler: Callable) -> None:
        self._action_handlers[action_type] = handler

    # ── DAG creation ─────────────────────────────────────────────────

    def create_dag(
        self,
        name: str,
        nodes: list[dict],
        description: str = "",
    ) -> DAG:
        dag_id = str(uuid.uuid4())[:12]
        now = time.time()

        dag_nodes = {}
        for n in nodes:
            node = DAGNode(
                node_id=n["node_id"],
                name=n.get("name", n["node_id"]),
                action_type=n["action_type"],
                params=n.get("params", {}),
                dependencies=n.get("dependencies", []),
                max_retries=n.get("max_retries", 3),
                backoff_seconds=n.get("backoff_seconds", 1.0),
                optional=n.get("optional", False),
            )
            dag_nodes[node.node_id] = node

        dag = DAG(
            dag_id=dag_id, name=name, description=description,
            nodes=dag_nodes, created_at=now,
        )

        self._save_dag(dag)
        return dag

    # ── Execution ────────────────────────────────────────────────────

    async def execute(self, dag_id: str) -> DAG:
        """Execute a DAG, running independent branches in parallel."""
        dag = self.get_dag(dag_id)
        if not dag:
            raise ValueError(f"DAG not found: {dag_id}")

        dag.status = "running"
        dag.started_at = time.time()
        self._save_dag(dag)

        # Execution loop: find ready nodes and run them in parallel
        while True:
            ready = self._get_ready_nodes(dag)
            if not ready:
                # Check if all done or blocked
                all_done = all(
                    n.status in (NodeStatus.COMPLETED.value, NodeStatus.SKIPPED.value, NodeStatus.FAILED.value)
                    for n in dag.nodes.values()
                )
                if all_done:
                    break
                # Check for deadlock
                has_pending = any(n.status == NodeStatus.PENDING.value for n in dag.nodes.values())
                if has_pending:
                    # Mark remaining as blocked
                    for n in dag.nodes.values():
                        if n.status == NodeStatus.PENDING.value:
                            n.status = NodeStatus.BLOCKED.value
                    break
                break

            # Execute ready nodes in parallel
            tasks = [self._execute_node(dag, node_id) for node_id in ready]
            await asyncio.gather(*tasks, return_exceptions=True)
            self._save_dag(dag)

        # Determine final status
        failed = [n for n in dag.nodes.values() if n.status == NodeStatus.FAILED.value and not n.optional]
        dag.status = "failed" if failed else "completed"
        dag.finished_at = time.time()
        self._save_dag(dag)

        return dag

    def _get_ready_nodes(self, dag: DAG) -> list[str]:
        """Find nodes whose dependencies are all completed/skipped."""
        ready = []
        for nid, node in dag.nodes.items():
            if node.status != NodeStatus.PENDING.value:
                continue
            deps_met = all(
                dag.nodes[dep].status in (NodeStatus.COMPLETED.value, NodeStatus.SKIPPED.value)
                for dep in node.dependencies
                if dep in dag.nodes
            )
            deps_failed = any(
                dag.nodes[dep].status == NodeStatus.FAILED.value
                for dep in node.dependencies
                if dep in dag.nodes
            )
            if deps_failed and not node.optional:
                node.status = NodeStatus.BLOCKED.value
                continue
            if deps_met:
                ready.append(nid)
        return ready

    async def _execute_node(self, dag: DAG, node_id: str) -> None:
        node = dag.nodes[node_id]
        node.status = NodeStatus.RUNNING.value
        node.started_at = time.time()

        handler = self._action_handlers.get(node.action_type)

        for attempt in range(node.max_retries + 1):
            try:
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        node.result = await handler(node.params)
                    else:
                        node.result = handler(node.params)
                else:
                    node.result = {"status": "no_handler", "action": node.action_type}

                node.status = NodeStatus.COMPLETED.value
                node.finished_at = time.time()
                node.retries = attempt
                return

            except Exception as e:
                node.retries = attempt
                if attempt < node.max_retries:
                    await asyncio.sleep(node.backoff_seconds * (2 ** attempt))
                else:
                    node.status = NodeStatus.FAILED.value if not node.optional else NodeStatus.SKIPPED.value
                    node.error = str(e)
                    node.finished_at = time.time()

    # ── Resume from checkpoint ───────────────────────────────────────

    async def resume(self, dag_id: str) -> DAG:
        """Resume an interrupted/failed DAG from last checkpoint."""
        dag = self.get_dag(dag_id)
        if not dag:
            raise ValueError(f"DAG not found: {dag_id}")

        # Reset failed/blocked nodes to pending for retry
        for node in dag.nodes.values():
            if node.status in (NodeStatus.FAILED.value, NodeStatus.BLOCKED.value):
                node.status = NodeStatus.PENDING.value
                node.error = None
                node.retries = 0

        return await self.execute(dag_id)

    # ── CRUD ─────────────────────────────────────────────────────────

    def _save_dag(self, dag: DAG) -> None:
        nodes_json = json.dumps({nid: n.to_dict() for nid, n in dag.nodes.items()})
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO dags
                (dag_id, name, description, nodes_json, status, created_at, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (dag.dag_id, dag.name, dag.description, nodes_json,
                 dag.status, dag.created_at, dag.started_at, dag.finished_at),
            )
            conn.commit()

    def get_dag(self, dag_id: str) -> DAG | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM dags WHERE dag_id = ?", (dag_id,)).fetchone()
            if not row:
                return None
            nodes_data = json.loads(row["nodes_json"])
            nodes = {}
            for nid, nd in nodes_data.items():
                nodes[nid] = DAGNode(
                    node_id=nd["node_id"], name=nd["name"],
                    action_type=nd["action_type"], params=nd.get("params", {}),
                    dependencies=nd.get("dependencies", []),
                    status=nd.get("status", "pending"),
                    result=nd.get("result"),
                    error=nd.get("error"),
                    retries=nd.get("retries", 0),
                    optional=nd.get("optional", False),
                    started_at=nd.get("started_at"),
                    finished_at=nd.get("finished_at"),
                )
            return DAG(
                dag_id=row["dag_id"], name=row["name"],
                description=row["description"], nodes=nodes,
                status=row["status"], created_at=row["created_at"],
                started_at=row["started_at"], finished_at=row["finished_at"],
            )

    def list_dags(self, status: str | None = None, limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    "SELECT dag_id, name, status, created_at, started_at, finished_at FROM dags WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT dag_id, name, status, created_at, started_at, finished_at FROM dags ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_dag(self, dag_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute("DELETE FROM dags WHERE dag_id = ?", (dag_id,))
            conn.commit()
            return cur.rowcount > 0


# ── Singleton ────────────────────────────────────────────────────────────

_executor: DAGExecutor | None = None


def get_dag_executor() -> DAGExecutor:
    global _executor
    if _executor is None:
        _executor = DAGExecutor()
    return _executor
