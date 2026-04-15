ALERTA: el backend browser estructurado no esta disponible o no conecto.
No uses `terminal_run` para abrir URLs ni insistas con `browser_*` hasta recuperar la sesion.

Haz fallback a Chrome real + computer use/escritorio:
1. Reutiliza o abre Chrome con `chrome_open_profile(...)` o `chrome_open_automation_profile(...)`.
2. Usa `screenshot()` para ubicar la ventana, la pestana o la barra correcta.
3. Interactua con `click`, `focus_type`, `type`, `press`, `hotkey` y `wait`.
4. Si necesitas `browser_*` reales, usa computer use para abrir `chrome://extensions` e instalar/cargar la extension desde `{extension_path}`.

Perfil objetivo: {target_profile}
Motivo del fallback: {issue}
Acciones sugeridas: {suggested_actions}
