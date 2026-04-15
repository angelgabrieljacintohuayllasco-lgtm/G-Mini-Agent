"""
Role-Based Access Control (RBAC) system.

Roles: owner, operator, approver, auditor, viewer
Policies: YAML-based per user, session, mode, skill, environment.
Precedence: hard_restrictions > deny > conditional > allow > default_deny
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import config


# ── Roles ────────────────────────────────────────────────────────────────

class Role(str, Enum):
    OWNER = "owner"
    OPERATOR = "operator"
    APPROVER = "approver"
    AUDITOR = "auditor"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.OWNER: 100,
    Role.OPERATOR: 80,
    Role.APPROVER: 60,
    Role.AUDITOR: 40,
    Role.VIEWER: 20,
}

# Default capabilities per role
ROLE_CAPABILITIES: dict[Role, set[str]] = {
    Role.OWNER: {
        "manage_roles", "manage_policies", "manage_config",
        "execute_actions", "approve_actions", "view_audit",
        "manage_skills", "manage_nodes", "manage_gateway",
        "manage_canvas", "manage_modes", "manage_budget",
        "export_data", "manage_sandbox",
    },
    Role.OPERATOR: {
        "execute_actions", "manage_skills", "manage_nodes",
        "manage_canvas", "manage_modes", "view_audit",
        "export_data",
    },
    Role.APPROVER: {
        "approve_actions", "view_audit", "execute_actions",
    },
    Role.AUDITOR: {
        "view_audit", "export_data",
    },
    Role.VIEWER: {
        "view_audit",
    },
}


# ── Policy ───────────────────────────────────────────────────────────────

class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"
    HARD_RESTRICT = "hard_restrict"


EFFECT_PRIORITY = {
    PolicyEffect.HARD_RESTRICT: 400,
    PolicyEffect.DENY: 300,
    PolicyEffect.CONDITIONAL: 200,
    PolicyEffect.ALLOW: 100,
}


@dataclass
class PolicyRule:
    rule_id: str
    effect: PolicyEffect
    action_patterns: list[str] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class PolicyDecision:
    allowed: bool
    effect: PolicyEffect
    rule_id: str = ""
    reason: str = ""
    requires_approval: bool = False


# ── RBAC Manager ─────────────────────────────────────────────────────────

class RBACManager:
    """Manages roles, users, and policy evaluation."""

    def __init__(self) -> None:
        db_path = config.get("security", "rbac", "db_path") or "data/rbac.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._policies: list[PolicyRule] = []
        self._init_db()
        self._load_default_policies()

    # ── DB ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rbac_users (
                    user_id   TEXT PRIMARY KEY,
                    name      TEXT NOT NULL,
                    role      TEXT NOT NULL DEFAULT 'viewer',
                    active    INTEGER NOT NULL DEFAULT 1,
                    created   REAL NOT NULL,
                    updated   REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rbac_sessions (
                    session_id   TEXT PRIMARY KEY,
                    user_id      TEXT NOT NULL,
                    role_override TEXT,
                    started      REAL NOT NULL,
                    expires      REAL,
                    active       INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES rbac_users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rbac_policies (
                    rule_id     TEXT PRIMARY KEY,
                    effect      TEXT NOT NULL,
                    spec_json   TEXT NOT NULL,
                    created     REAL NOT NULL,
                    updated     REAL NOT NULL
                )
            """)
            # Seed owner if empty
            row = conn.execute("SELECT COUNT(*) FROM rbac_users").fetchone()
            if row and row[0] == 0:
                now = time.time()
                conn.execute(
                    "INSERT INTO rbac_users (user_id, name, role, active, created, updated) VALUES (?, ?, ?, 1, ?, ?)",
                    ("local_owner", "Owner (local)", Role.OWNER.value, now, now),
                )
            conn.commit()

    # ── Users ────────────────────────────────────────────────────────

    def list_users(self) -> list[dict]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM rbac_users ORDER BY created").fetchall()
            return [dict(r) for r in rows]

    def get_user(self, user_id: str) -> dict | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM rbac_users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def create_user(self, user_id: str, name: str, role: str = "viewer") -> dict:
        if role not in [r.value for r in Role]:
            raise ValueError(f"Invalid role: {role}")
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO rbac_users (user_id, name, role, active, created, updated) VALUES (?, ?, ?, 1, ?, ?)",
                (user_id, name, role, now, now),
            )
            conn.commit()
        logger.info(f"RBAC user created: {user_id} role={role}")
        return {"user_id": user_id, "name": name, "role": role, "active": 1}

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        if new_role not in [r.value for r in Role]:
            raise ValueError(f"Invalid role: {new_role}")
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                "UPDATE rbac_users SET role = ?, updated = ? WHERE user_id = ?",
                (new_role, time.time(), user_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def deactivate_user(self, user_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute(
                "UPDATE rbac_users SET active = 0, updated = ? WHERE user_id = ?",
                (time.time(), user_id),
            )
            conn.commit()
            return cur.rowcount > 0

    # ── Permission checks ────────────────────────────────────────────

    def get_user_role(self, user_id: str) -> Role:
        user = self.get_user(user_id)
        if not user or not user.get("active"):
            return Role.VIEWER
        try:
            return Role(user["role"])
        except ValueError:
            return Role.VIEWER

    def has_capability(self, user_id: str, capability: str) -> bool:
        role = self.get_user_role(user_id)
        return capability in ROLE_CAPABILITIES.get(role, set())

    def check_permission(self, user_id: str, capability: str) -> dict:
        role = self.get_user_role(user_id)
        allowed = capability in ROLE_CAPABILITIES.get(role, set())
        return {
            "user_id": user_id,
            "role": role.value,
            "capability": capability,
            "allowed": allowed,
            "reason": f"Role '{role.value}' {'has' if allowed else 'lacks'} capability '{capability}'",
        }

    # ── Policy evaluation ────────────────────────────────────────────

    def _load_default_policies(self) -> None:
        """Load hardcoded default policies."""
        self._policies = [
            PolicyRule(
                rule_id="hard_no_unauthorized_access",
                effect=PolicyEffect.HARD_RESTRICT,
                action_patterns=["unauthorized_*", "bypass_security_*"],
                description="Always block unauthorized system access",
            ),
            PolicyRule(
                rule_id="hard_no_mass_delete",
                effect=PolicyEffect.HARD_RESTRICT,
                action_patterns=["mass_delete_*", "wipe_*", "format_disk"],
                description="Block mass data destruction without explicit confirm",
            ),
            PolicyRule(
                rule_id="conditional_file_write",
                effect=PolicyEffect.CONDITIONAL,
                action_patterns=["file_write_*", "file_delete_*"],
                roles=["viewer", "auditor"],
                conditions={"requires_role_min": "operator"},
                description="File writes need operator or above",
            ),
            PolicyRule(
                rule_id="conditional_payments",
                effect=PolicyEffect.CONDITIONAL,
                action_patterns=["payment_*", "purchase_*"],
                conditions={"requires_approval": True},
                description="Payments always need approval",
            ),
        ]
        # Load custom policies from DB
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM rbac_policies").fetchall()
                for row in rows:
                    spec = json.loads(row["spec_json"])
                    rule = PolicyRule(
                        rule_id=row["rule_id"],
                        effect=PolicyEffect(row["effect"]),
                        action_patterns=spec.get("action_patterns", []),
                        modes=spec.get("modes", []),
                        skills=spec.get("skills", []),
                        roles=spec.get("roles", []),
                        conditions=spec.get("conditions", {}),
                        description=spec.get("description", ""),
                    )
                    self._policies.append(rule)
        except Exception as e:
            logger.warning(f"Failed to load custom policies: {e}")

    def evaluate_policy(
        self,
        action_type: str,
        user_id: str = "local_owner",
        mode: str = "",
        skill: str = "",
    ) -> PolicyDecision:
        """Evaluate policies for an action. Precedence: hard > deny > conditional > allow > default_deny."""
        import fnmatch

        role = self.get_user_role(user_id)
        best_decision: PolicyDecision | None = None
        best_priority = -1

        for rule in self._policies:
            # Check if rule matches action
            action_match = not rule.action_patterns or any(
                fnmatch.fnmatch(action_type, pat) for pat in rule.action_patterns
            )
            if not action_match:
                continue

            # Check role filter
            if rule.roles and role.value not in rule.roles:
                continue

            # Check mode filter
            if rule.modes and mode and mode not in rule.modes:
                continue

            # Check skill filter
            if rule.skills and skill and skill not in rule.skills:
                continue

            priority = EFFECT_PRIORITY.get(rule.effect, 0)
            if priority > best_priority:
                best_priority = priority

                if rule.effect == PolicyEffect.HARD_RESTRICT:
                    best_decision = PolicyDecision(
                        allowed=False, effect=rule.effect,
                        rule_id=rule.rule_id, reason=rule.description,
                    )
                elif rule.effect == PolicyEffect.DENY:
                    best_decision = PolicyDecision(
                        allowed=False, effect=rule.effect,
                        rule_id=rule.rule_id, reason=rule.description,
                    )
                elif rule.effect == PolicyEffect.CONDITIONAL:
                    needs_approval = rule.conditions.get("requires_approval", False)
                    min_role = rule.conditions.get("requires_role_min", "")
                    if min_role:
                        min_level = ROLE_HIERARCHY.get(Role(min_role), 0)
                        current_level = ROLE_HIERARCHY.get(role, 0)
                        if current_level >= min_level:
                            best_decision = PolicyDecision(
                                allowed=True, effect=PolicyEffect.ALLOW,
                                rule_id=rule.rule_id, reason="Role sufficient",
                            )
                        else:
                            best_decision = PolicyDecision(
                                allowed=False, effect=rule.effect,
                                rule_id=rule.rule_id,
                                reason=f"Requires role >= {min_role}",
                                requires_approval=True,
                            )
                    elif needs_approval:
                        best_decision = PolicyDecision(
                            allowed=False, effect=rule.effect,
                            rule_id=rule.rule_id,
                            reason=rule.description,
                            requires_approval=True,
                        )
                elif rule.effect == PolicyEffect.ALLOW:
                    best_decision = PolicyDecision(
                        allowed=True, effect=rule.effect,
                        rule_id=rule.rule_id, reason=rule.description,
                    )

        if best_decision:
            return best_decision

        # Default deny
        return PolicyDecision(
            allowed=False,
            effect=PolicyEffect.DENY,
            rule_id="default_deny",
            reason="No explicit policy allows this action",
        )

    # ── Custom policy CRUD ───────────────────────────────────────────

    def add_policy(self, rule: PolicyRule) -> None:
        spec = {
            "action_patterns": rule.action_patterns,
            "modes": rule.modes,
            "skills": rule.skills,
            "roles": rule.roles,
            "conditions": rule.conditions,
            "description": rule.description,
        }
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO rbac_policies (rule_id, effect, spec_json, created, updated) VALUES (?, ?, ?, ?, ?)",
                (rule.rule_id, rule.effect.value, json.dumps(spec), now, now),
            )
            conn.commit()
        self._policies.append(rule)
        logger.info(f"RBAC policy added: {rule.rule_id}")

    def remove_policy(self, rule_id: str) -> bool:
        with sqlite3.connect(str(self._db_path)) as conn:
            cur = conn.execute("DELETE FROM rbac_policies WHERE rule_id = ?", (rule_id,))
            conn.commit()
        self._policies = [p for p in self._policies if p.rule_id != rule_id]
        return cur.rowcount > 0

    def list_policies(self) -> list[dict]:
        result = []
        for p in self._policies:
            result.append({
                "rule_id": p.rule_id,
                "effect": p.effect.value,
                "action_patterns": p.action_patterns,
                "modes": p.modes,
                "skills": p.skills,
                "roles": p.roles,
                "conditions": p.conditions,
                "description": p.description,
            })
        return result


# ── Singleton ────────────────────────────────────────────────────────────

_rbac_manager: RBACManager | None = None


def get_rbac() -> RBACManager:
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def set_rbac(mgr: RBACManager) -> None:
    global _rbac_manager
    _rbac_manager = mgr
