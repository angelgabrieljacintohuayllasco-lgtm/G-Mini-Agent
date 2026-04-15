## Servidores MCP disponibles y sus herramientas

Los siguientes servidores MCP están configurados y listos. Puedes usar las herramientas directamente con `mcp_call_tool(server_id=..., tool=..., arguments={...})` SIN necesidad de listar primero.

{{mcp_tools_summary}}

**Uso directo:** No necesitas ejecutar `mcp_list_servers` ni `mcp_list_tools` antes de usar una herramienta MCP. Ya conoces las tools disponibles arriba. Simplemente llama `mcp_call_tool` con el server_id, nombre de tool y argumentos correctos.
