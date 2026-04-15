Resultado de las acciones ejecutadas:
{action_feedback}

Usa este feedback para decidir el siguiente paso.
No asumas que la tarea termino solo porque una accion se ejecuto sin error tecnico.
Si necesitas confirmar estado visual o de archivos, hazlo antes de cerrar la tarea.
Si una accion `browser_*` falla porque no hay backend browser, extension o sesion conectada, replanifica a Chrome real + `screenshot()` + computer use/escritorio; no uses `terminal_run` para suplantar la navegacion web.
Si la tarea requiere dejar un archivo local verificable, prefiere `file_write_text(path=..., text=...)` para persistirlo y `file_exists(path=...)` para confirmarlo.
No dependas de cuadros "Guardar como" ni de atajos de teclado que puedan cambiar segun el idioma o la aplicacion activa.
Si el sistema te entrega datos confirmados reutilizables, usa esos valores exactos al escribir texto o reemplazar placeholders como {resultado}, {respuesta}, {titulo}, {ruta}, {archivo}, {contenido} o {coincidencia}.
