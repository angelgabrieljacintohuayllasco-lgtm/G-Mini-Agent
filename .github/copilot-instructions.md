# Copilot instructions

Cuando el usuario pida corregir, editar, refactorizar, modificar o integrar algo:

- Realiza cambios reales en los archivos del workspace siempre que sea posible.
- No escribas respuestas del tipo “procedo a realizar cambios” si aún no editaste nada.
- No inventes diffs, parches ni archivos inexistentes.
- Si falta contexto, identifica qué archivo o símbolo falta y dilo claramente.
- Antes de cambiar código, revisa las referencias relacionadas.
- Mantén el estilo y convenciones actuales del repositorio.
- Haz cambios mínimos, seguros y consistentes.
- Si tocas una función pública, revisa imports, tipos, tests y usos relacionados.
- Al finalizar, responde con:
  - archivos modificados
  - resumen breve de cambios reales
  - pendientes o limitaciones reales
- Nunca afirmes que un cambio fue aplicado si no quedó reflejado en el workspace.