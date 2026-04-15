No hubo progreso observable despues de varios intentos recientes.

Resultados recientes:
{recent_results}

Debes cambiar de estrategia antes de seguir.

Reglas:
- No repitas la misma accion o la misma familia de acciones si el estado no cambio.
- Primero verifica el estado actual con herramientas de lectura apropiadas para el contexto.
- Si estas en navegador, prioriza lectura del DOM, estado de pagina, URL, tabs, snapshot o extraccion de contenido antes de volver a interactuar.
- Si estas en escritorio, toma una captura nueva y reasigna coordenadas o usa una estrategia distinta.
- Si el bloqueo es guardar o verificar un archivo local, evita cuadros de dialogo fragiles y usa `file_write_text(...)` + `file_exists(...)`.
- Si una accion fallo o no produjo cambio visible, explica brevemente el nuevo plan y ejecuta otra secuencia.

Continua con acciones concretas o finaliza con `[ACTION:task_complete(summary=...)]` si la tarea ya termino.
