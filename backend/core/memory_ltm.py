"""
Long-Term Memory with semantic search (RAG).

Stores facts, preferences, task history, and learnings as embeddings.
Uses SQLite + lightweight vector similarity for retrieval.
No external vector DB dependency — uses numpy cosine similarity.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from backend.config import config


class MemoryCategory(str, Enum):
    FACT = "fact"              # User facts: "Mi empresa se llama Acme"
    PREFERENCE = "preference"  # Preferences: "Prefiero respuestas concisas"
    TASK = "task"              # Task history: "Desplegamos v2.3 el martes"
    LEARNING = "learning"      # Agent learnings: "El usuario prefiere Python sobre JS"
    ENTITY = "entity"          # Named entities: persons, companies, projects
    RELATIONSHIP = "relationship"  # Extracted from KG
    SKILL = "skill_memory"    # Skill execution patterns


@dataclass
class MemoryEntry:
    memory_id: str
    category: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5       # 0.0 - 1.0
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    expires_at: float | None = None


class LongTermMemory:
    """Persistent memory with semantic search capabilities."""

    EMBEDDING_DIM = 384  # Sentence-transformer mini default

    def __init__(self) -> None:
        db_path = config.get("memory", "db_path") or "data/memory_ltm.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder = None
        self._max_memories = config.get("memory", "max_memories") or 5000
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    memory_id     TEXT PRIMARY KEY,
                    category      TEXT NOT NULL,
                    content       TEXT NOT NULL,
                    embedding     BLOB,
                    metadata      TEXT NOT NULL DEFAULT '{}',
                    importance    REAL NOT NULL DEFAULT 0.5,
                    access_count  INTEGER NOT NULL DEFAULT 0,
                    created_at    REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    expires_at    REAL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ltm_category ON long_term_memory(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ltm_importance ON long_term_memory(importance DESC)"
            )
            conn.commit()

    # ── Embedding ────────────────────────────────────────────────────

    def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding. Uses simple TF-IDF-like hash if no model available."""
        # Lightweight: deterministic hash-based embedding (no ML dependency)
        # Works well enough for keyword-level similarity
        tokens = text.lower().split()
        vec = np.zeros(self.EMBEDDING_DIM, dtype=np.float32)
        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            indices = [(h >> (j * 8)) % self.EMBEDDING_DIM for j in range(4)]
            for idx in indices:
                vec[idx] += 1.0 / (1.0 + i * 0.1)  # Position decay
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # ── CRUD ─────────────────────────────────────────────────────────

    def store(
        self,
        content: str,
        category: str = "fact",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
        expires_at: float | None = None,
    ) -> str:
        """Store a memory entry with embedding."""
        memory_id = hashlib.sha256(
            f"{content}:{category}:{time.time()}".encode()
        ).hexdigest()[:16]
        embedding = self._get_embedding(content)
        now = time.time()

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO long_term_memory
                (memory_id, category, content, embedding, metadata, importance,
                 access_count, created_at, last_accessed, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                (
                    memory_id, category, content,
                    np.array(embedding, dtype=np.float32).tobytes(),
                    json.dumps(metadata or {}),
                    importance, now, now, expires_at,
                ),
            )
            conn.commit()

        logger.debug(f"LTM stored: [{category}] {content[:80]}...")
        self._evict_if_needed()
        return memory_id

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_similarity: float = 0.1,
    ) -> list[dict]:
        """Semantic search over memories."""
        query_emb = self._get_embedding(query)

        where = ""
        params: list[Any] = []
        if category:
            where = "WHERE category = ?"
            params.append(category)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM long_term_memory {where}", params
            ).fetchall()

        # Score and rank
        scored = []
        now = time.time()
        for row in rows:
            # Skip expired
            if row["expires_at"] and row["expires_at"] < now:
                continue
            emb_bytes = row["embedding"]
            if not emb_bytes:
                continue
            stored_emb = np.frombuffer(emb_bytes, dtype=np.float32).tolist()
            sim = self._cosine_similarity(query_emb, stored_emb)

            # Boost by importance and recency
            recency_boost = max(0, 1.0 - (now - row["last_accessed"]) / (86400 * 30))
            final_score = sim * 0.7 + row["importance"] * 0.2 + recency_boost * 0.1

            if sim >= min_similarity:
                scored.append({
                    "memory_id": row["memory_id"],
                    "category": row["category"],
                    "content": row["content"],
                    "similarity": round(sim, 4),
                    "score": round(final_score, 4),
                    "importance": row["importance"],
                    "metadata": json.loads(row["metadata"]),
                    "access_count": row["access_count"],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        results = scored[:top_k]

        # Update access counts
        if results:
            with sqlite3.connect(str(self._db_path)) as conn:
                for r in results:
                    conn.execute(
                        "UPDATE long_term_memory SET access_count = access_count + 1, last_accessed = ? WHERE memory_id = ?",
                        (now, r["memory_id"]),
                    )
                conn.commit()

        return results

    def get_context_injection(self, query: str, max_tokens: int = 500) -> str:
        """Get relevant memories formatted for system prompt injection."""
        results = self.search(query, top_k=10)
        if not results:
            return ""

        lines = ["[Memoria relevante del usuario]"]
        char_budget = max_tokens * 4  # ~4 chars per token
        used = len(lines[0])

        for r in results:
            line = f"- [{r['category']}] {r['content']}"
            if used + len(line) > char_budget:
                break
            lines.append(line)
            used += len(line)

        return "\n".join(lines)

    def list_memories(
        self,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT memory_id, category, content, importance, access_count, created_at, last_accessed, metadata "
                f"FROM long_term_memory {where} ORDER BY importance DESC, last_accessed DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            return [dict(r) for r in rows]

    def delete(self, memory_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute("DELETE FROM long_term_memory WHERE memory_id = ?", (memory_id,))
            conn.commit()
            return cur.rowcount > 0

    def update_importance(self, memory_id: str, importance: float) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                "UPDATE long_term_memory SET importance = ? WHERE memory_id = ?",
                (max(0.0, min(1.0, importance)), memory_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def count(self) -> int:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM long_term_memory").fetchone()
            return row[0] if row else 0

    def _evict_if_needed(self) -> None:
        """LRU eviction when exceeding max memories."""
        count = self.count()
        if count <= self._max_memories:
            return
        to_remove = count - self._max_memories + 100  # Remove extra buffer
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "DELETE FROM long_term_memory WHERE memory_id IN "
                "(SELECT memory_id FROM long_term_memory ORDER BY importance ASC, last_accessed ASC LIMIT ?)",
                (to_remove,),
            )
            conn.commit()
        logger.info(f"LTM evicted {to_remove} low-importance memories")

    def cleanup_expired(self) -> int:
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                "DELETE FROM long_term_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            )
            conn.commit()
            return cur.rowcount


# ── Singleton ────────────────────────────────────────────────────────────

_ltm: LongTermMemory | None = None


def get_ltm() -> LongTermMemory:
    global _ltm
    if _ltm is None:
        _ltm = LongTermMemory()
    return _ltm
