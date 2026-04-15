"""
G-Mini Agent - Skill Runtime (STUB)
Runtime para ejecutar tools de skills registrados.
"""

from typing import Any, Dict


class SkillRuntime:
    """Runtime para ejecutar skills/tools."""
    
    def __init__(self, registry=None):
        self._registry = registry
    
    def run_tool(self, skill_id: str, tool: str, input_data: Dict[str, Any], 
                 timeout_seconds: int = 30) -> Dict[str, Any]:
        """Ejecuta un tool específico de un skill."""
        return {
            "success": False,
            "skill_id": skill_id,
            "tool": tool,
            "error": f"SkillRuntime stub: skill '{skill_id}' / tool '{tool}' no implementado"
        }


def get_skill_runtime(registry=None) -> SkillRuntime:
    """Singleton global."""
    return SkillRuntime(registry)
