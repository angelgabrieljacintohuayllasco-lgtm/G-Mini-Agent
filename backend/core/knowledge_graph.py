"""
Knowledge Graph — local graph database using NetworkX.

Entities: Persons, Companies, Projects, Products, Events, Tasks
Relations: works_at, client_of, competes_with, assigned_to, depends_on, interested_in
Auto-constructs graph from conversations and tasks.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    logger.warning("networkx not available — Knowledge Graph will use SQLite fallback")


class EntityType:
    PERSON = "person"
    COMPANY = "company"
    PROJECT = "project"
    PRODUCT = "product"
    EVENT = "event"
    TASK = "task"
    LOCATION = "location"
    CONCEPT = "concept"


VALID_RELATIONS = {
    "works_at", "client_of", "competes_with", "assigned_to",
    "depends_on", "interested_in", "owns", "manages",
    "created_by", "part_of", "related_to", "located_in",
    "attended", "scheduled_for", "blocked_by", "knows",
}


@dataclass
class Entity:
    entity_id: str
    entity_type: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class Relation:
    source_id: str
    target_id: str
    relation_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = 0.0


class KnowledgeGraph:
    """Local Knowledge Graph with entity/relation management."""

    def __init__(self) -> None:
        db_path = config.get("memory", "knowledge_graph_db_path") or "data/memory_ltm.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._graph: Any = None
        self._init_db()
        self._load_graph()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_entities (
                    entity_id   TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    name        TEXT NOT NULL,
                    properties  TEXT NOT NULL DEFAULT '{}',
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_relations (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id     TEXT NOT NULL,
                    target_id     TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    properties    TEXT NOT NULL DEFAULT '{}',
                    confidence    REAL NOT NULL DEFAULT 1.0,
                    created_at    REAL NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES kg_entities(entity_id),
                    FOREIGN KEY (target_id) REFERENCES kg_entities(entity_id),
                    UNIQUE(source_id, target_id, relation_type)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_ent_type ON kg_entities(entity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_rel_src ON kg_relations(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_rel_tgt ON kg_relations(target_id)")
            conn.commit()

    def _load_graph(self) -> None:
        """Load graph from SQLite into NetworkX (if available)."""
        if not HAS_NETWORKX:
            return

        self._graph = nx.DiGraph()

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            entities = conn.execute("SELECT * FROM kg_entities").fetchall()
            for e in entities:
                self._graph.add_node(
                    e["entity_id"],
                    entity_type=e["entity_type"],
                    name=e["name"],
                    properties=json.loads(e["properties"]),
                )
            relations = conn.execute("SELECT * FROM kg_relations").fetchall()
            for r in relations:
                self._graph.add_edge(
                    r["source_id"], r["target_id"],
                    relation_type=r["relation_type"],
                    confidence=r["confidence"],
                    properties=json.loads(r["properties"]),
                )

        logger.info(f"KG loaded: {self._graph.number_of_nodes()} entities, {self._graph.number_of_edges()} relations")

    # ── Entity CRUD ──────────────────────────────────────────────────

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        now = time.time()
        props = properties or {}

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO kg_entities
                (entity_id, entity_type, name, properties, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (entity_id, entity_type, name, json.dumps(props), now, now),
            )
            conn.commit()

        if self._graph is not None:
            self._graph.add_node(
                entity_id, entity_type=entity_type, name=name, properties=props,
            )

        return Entity(entity_id=entity_id, entity_type=entity_type, name=name,
                      properties=props, created_at=now, updated_at=now)

    def get_entity(self, entity_id: str) -> Entity | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM kg_entities WHERE entity_id = ?", (entity_id,)
            ).fetchone()
            if not row:
                return None
            return Entity(
                entity_id=row["entity_id"],
                entity_type=row["entity_type"],
                name=row["name"],
                properties=json.loads(row["properties"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def update_entity(self, entity_id: str, properties: dict[str, Any]) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT properties FROM kg_entities WHERE entity_id = ?", (entity_id,)
            ).fetchone()
            if not row:
                return False
            existing = json.loads(row[0])
            existing.update(properties)
            conn.execute(
                "UPDATE kg_entities SET properties = ?, updated_at = ? WHERE entity_id = ?",
                (json.dumps(existing), time.time(), entity_id),
            )
            conn.commit()

        if self._graph is not None and entity_id in self._graph:
            self._graph.nodes[entity_id]["properties"].update(properties)

        return True

    def delete_entity(self, entity_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM kg_relations WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
            cur = conn.execute("DELETE FROM kg_entities WHERE entity_id = ?", (entity_id,))
            conn.commit()

        if self._graph is not None and entity_id in self._graph:
            self._graph.remove_node(entity_id)

        return cur.rowcount > 0

    def list_entities(self, entity_type: str | None = None, limit: int = 100) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if entity_type:
                rows = conn.execute(
                    "SELECT * FROM kg_entities WHERE entity_type = ? ORDER BY updated_at DESC LIMIT ?",
                    (entity_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM kg_entities ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["properties"] = json.loads(d["properties"])
                result.append(d)
            return result

    # ── Relation CRUD ────────────────────────────────────────────────

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        confidence: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> Relation | None:
        if relation_type not in VALID_RELATIONS:
            logger.warning(f"Invalid relation type: {relation_type}")
            return None

        now = time.time()
        props = properties or {}

        with sqlite3.connect(str(self._db_path)) as conn:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO kg_relations
                    (source_id, target_id, relation_type, properties, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (source_id, target_id, relation_type, json.dumps(props), confidence, now),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return None

        if self._graph is not None:
            self._graph.add_edge(
                source_id, target_id,
                relation_type=relation_type,
                confidence=confidence,
                properties=props,
            )

        return Relation(
            source_id=source_id, target_id=target_id,
            relation_type=relation_type, properties=props,
            confidence=confidence, created_at=now,
        )

    def get_relations(self, entity_id: str, direction: str = "both") -> list[dict]:
        """Get relations for an entity. direction: 'outgoing', 'incoming', 'both'."""
        results = []
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if direction in ("outgoing", "both"):
                rows = conn.execute(
                    "SELECT * FROM kg_relations WHERE source_id = ?", (entity_id,)
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    d["properties"] = json.loads(d["properties"])
                    d["direction"] = "outgoing"
                    results.append(d)
            if direction in ("incoming", "both"):
                rows = conn.execute(
                    "SELECT * FROM kg_relations WHERE target_id = ?", (entity_id,)
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    d["properties"] = json.loads(d["properties"])
                    d["direction"] = "incoming"
                    results.append(d)
        return results

    def remove_relation(self, source_id: str, target_id: str, relation_type: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                "DELETE FROM kg_relations WHERE source_id = ? AND target_id = ? AND relation_type = ?",
                (source_id, target_id, relation_type),
            )
            conn.commit()

        if self._graph is not None and self._graph.has_edge(source_id, target_id):
            self._graph.remove_edge(source_id, target_id)

        return cur.rowcount > 0

    # ── Queries ──────────────────────────────────────────────────────

    def find_path(self, source_id: str, target_id: str) -> list[str] | None:
        """Find shortest path between two entities."""
        if self._graph is None:
            return None
        try:
            return nx.shortest_path(self._graph, source_id, target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_neighbors(self, entity_id: str, depth: int = 1) -> dict:
        """Get entity neighborhood up to N hops."""
        if self._graph is None:
            # Fallback to SQL
            return {"entity_id": entity_id, "neighbors": self.get_relations(entity_id)}

        if entity_id not in self._graph:
            return {"entity_id": entity_id, "neighbors": []}

        subgraph_nodes = set()
        frontier = {entity_id}
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                for n in self._graph.neighbors(node):
                    if n not in subgraph_nodes:
                        next_frontier.add(n)
                for n in self._graph.predecessors(node):
                    if n not in subgraph_nodes:
                        next_frontier.add(n)
            subgraph_nodes |= frontier
            frontier = next_frontier
        subgraph_nodes |= frontier

        nodes = []
        for n in subgraph_nodes:
            data = self._graph.nodes.get(n, {})
            nodes.append({
                "entity_id": n,
                "name": data.get("name", n),
                "entity_type": data.get("entity_type", ""),
            })

        edges = []
        for u, v, data in self._graph.edges(data=True):
            if u in subgraph_nodes and v in subgraph_nodes:
                edges.append({
                    "source": u, "target": v,
                    "relation_type": data.get("relation_type", "related_to"),
                })

        return {"entity_id": entity_id, "nodes": nodes, "edges": edges}

    def get_stats(self) -> dict:
        with sqlite3.connect(str(self._db_path)) as conn:
            ent_count = conn.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
            rel_count = conn.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]
            types = conn.execute(
                "SELECT entity_type, COUNT(*) FROM kg_entities GROUP BY entity_type"
            ).fetchall()
        return {
            "entities": ent_count,
            "relations": rel_count,
            "entity_types": {t[0]: t[1] for t in types},
            "networkx_available": HAS_NETWORKX,
        }


# ── Singleton ────────────────────────────────────────────────────────────

_kg: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg
