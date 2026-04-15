"""
G-Mini Agent - MCP Server Registry (STUB)
Registro de servidores MCP disponibles.
Para producción: cargar desde config/servers.yaml
"""

from typing import Any, Dict, List


class MCPRegistry:
    """Registro de servidores MCP disponibles."""
    
    def __init__(self):
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._enabled = False
    
    def list_servers(self) -> Dict[str, Any]:
        """Lista todos los servidores registrados."""
        return {
            "enabled": self._enabled,
            "servers": list(self._servers.values())
        }
    
    def get_server(self, server_id: str) -> Dict[str, Any] | None:
        """Obtiene servidor por ID."""
        return self._servers.get(server_id)
    
    def get_runtime_server(self, server_id: str) -> Dict[str, Any] | None:
        """Obtiene config runtime-validado del servidor."""
        server = self.get_server(server_id)
        if not server or not server.get("ready", False):
            return None
        return server
    
    def register_server(self, server_config: Dict[str, Any]) -> str:
        """Registra/agrega servidor."""
        server_id = server_config.get("id", f"mcp-{len(self._servers)}")
        self._servers[server_id] = server_config
        return server_id
    
    def enable(self, enabled: bool = True) -> None:
        """Habilita/deshabilita el registry."""
        self._enabled = enabled


# Constantes para validación de transportes
VALID_STDIO_TRANSPORTS = ["stdio"]


# Singleton global
_registry_instance = MCPRegistry()
def get_mcp_registry() -> MCPRegistry:
    return _registry_instance
