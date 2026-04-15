{user_request}

[SISTEMA: Esta es una tarea web. Prioriza acciones browser_* para navegar, interactuar y verificar cuando el backend estructurado este disponible.
Flujo recomendado:
1. Conecta un perfil o sesion de navegador con `browser_use_profile(...)` o `browser_use_automation_profile(...)`.
2. Navega a la URL o punto de inicio adecuado.
3. Usa selectores, texto visible, DOM o JavaScript cuando sea util.
4. Verifica con `browser_snapshot`, `browser_extract`, `browser_page_info` o comprobaciones equivalentes.
Si el backend browser falla porque no hay `browser-use` o la extension no esta conectada, NO cambies a `terminal_run` para abrir URLs.
Haz fallback a Chrome real + computer use/escritorio: `chrome_open_profile(...)` o `chrome_open_automation_profile(...)`, luego `screenshot()`, `click`, `focus_type`, `type`, `press`, `hotkey` y `wait`.
Si hace falta, puedes usar computer use para abrir `chrome://extensions` e instalar la extension desde `assets/extension` en el perfil deseado.]
