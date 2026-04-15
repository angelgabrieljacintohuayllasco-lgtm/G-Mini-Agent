# G-Mini Agent — Roadmap Completo de Fases de Desarrollo

**Versión:** 1.0  
**Fecha:** 3 de abril de 2026  
**Basado en:** G-MINI-AGENT-DEFINICION.md v3.1

---

## Resumen Ejecutivo

## Estado Real Actual

**Fecha de corte:** 3 de abril de 2026

| Fase | Estado real | Notas |
|------|-------------|-------|
| 1 | Alta | Backend FastAPI + Socket.IO, router LLM multi-proveedor, memoria persistente, UI Electron con chat, config API keys, historial, system tray. |
| 2 | Alta | Screenshot mss, OCR multi-motor (Tesseract/EasyOCR/PaddleOCR), OmniParser, PyAutoGUI, ADB, loop agente con verificación visual, controles Start/Pause/Stop. |
| 3 | Media-Alta | Overlay Electron, TTS MeloTTS offline, STT Faster-Whisper, lipsync RMS, sprites 2D con 4 estados, barge-in, config voz. Pendiente: streaming realtime completo (OpenAI/Gemini/Grok Live). |
| 4 | Alta | Motor de modos con system prompts, modos custom YAML, sub-agentes con orquestador, critic gate con scores, approval UI, herencia de permisos, multi-shell (10 terminales). |
| 5 | Media | Extensión Chrome con WebSocket, ffmpeg, Google Calendar/Sheets, DALL-E, email base, redes sociales parcial. Pendiente: CRM completo (HubSpot/Salesforce), Notion, Airtable, CapCut, OBS. |
| 6 | Alta | Gateway con outbox persistente SQLite. WhatsApp Web (bridge Node), Telegram (polling + inline), Discord (discord.py), Slack (slack-sdk). Comandos remotos, aprobaciones tokenizadas, activación por mención. |
| 7 | Media-Alta | `node_manager.py` con protocolo WebSocket, superficies y permisos. `smart_home_manager.py` con bridge Home Assistant. API endpoints y panel UI. Pendiente: app companion móvil, node PC remota completa. |
| 8 | Media-Alta | `canvas.py` con motor de dashboards. `scheduler.py` persistente con cron/intervalo/heartbeat/evento/webhook, retries con backoff. `skill_runtime.py` aislado. Skills bundled parciales. Pendiente: registry remoto. |
| 9 | Alta | `cost_tracker.py` con ledger SQLite, presupuesto global/modo/tarea/sub-agente, checkpoints, recovery tras crash, close-to-tray, notificaciones gateway. `cost_optimizer.py` con auto-switch, compresión de contexto y priorización local. Pendiente: reporte semanal por gateway. |
| 10 | Completa | `rbac.py` (5 roles), `audit.py`, `sandbox.py`, `injection_detector.py`, `ethical_filter.py`, `rate_limiter.py`, `policy_engine.py` — 17 API endpoints, panel UI seguridad. |
| 11 | Completa | `memory_ltm.py` (búsqueda semántica), `session_compressor.py` (80k trigger), `knowledge_graph.py` (NetworkX) — 12 API endpoints, config completa. |
| 12 | Completa | `macro_engine.py` (grabación + replay), `rollback.py` (snapshots + undo) — 12 API endpoints, config completa. |
| 13 | Completa | `dag_executor.py` (ejecución paralela + checkpoints), `goal_engine.py` (KPIs + replanificación), `analytics.py` (dashboard ejecutivo) — 35 API endpoints, tab Analytics en UI. |
| 14 | Completa | `event_bus.py` (pub/sub + cola SQLite), `self_healing.py` (recovery por tipo de fallo), `artifact_versioning.py` (draft→staging→prod) — 20 API endpoints. |
| 15 | Completa | `etl_engine.py` (pipelines CSV/JSON/SQLite), `causal_alerts.py` (métricas + reglas), `rlhf_lite.py` (señales + preferencias EMA) — 22 API endpoints. |
| 16 | Completa | `autonomous_agents.py`: AgentManager, SOPGenerator, ABTestEngine, WhatIfSimulator — 30 API endpoints. |
| 17 | Completa | `productivity.py`: SmartClipboard, NotificationManager, PriceTracker, SystemOptimizer — 25 API endpoints. |
| 18 | Completa | `offline_sync.py`: OfflineManager, SyncManager, SkillDeprecation. `auto_updater.py`: AutoUpdater — 28 API endpoints. |

### Prioridad recomendada de desarrollo (siguiente iteración)

1. **Pulido para producción:** testing E2E de flujos críticos (Fase 2 loop agente, Fase 6 gateway, Fase 9 presupuesto).
2. **Robustez Fase 3:** completar streaming realtime (OpenAI Realtime API, Gemini Live, Grok Live Voice).
3. **Integraciones Fase 5:** conectores CRM reales (HubSpot/Salesforce), Notion, Airtable.
4. **Packaging Fase 18:** empaquetado NSIS con firma de código, Nuitka como alternativa, onboarding interactivo.
5. **Testing + docs:** cobertura de tests unitarios y documentación API (OpenAPI auto-generada por FastAPI).

| Fase | Nombre | Duración Est. | Objetivo |
|------|--------|---------------|---------|
| 1 | Chat con todos los LLMs + UI Electron | 3-4 sem | App funcional de chat con cualquier modelo |
| 2 | Ver pantalla + hacer clicks *(CORE DIFERENCIADOR)* | 4-5 sem | Agente que ve y controla la PC y Android |
| 3 | Personaje animado + voz | 4-5 sem | Asistente visual que habla y escucha |
| 4 | Sistema de Modos + Sub-Agentes | 4-5 sem | Multi-personalidad y capacidad multi-agente |
| 5 | Integraciones Externas | 3-4 sem | Conexión con herramientas y servicios |
| 6 | Gateway Multi-Canal | 3-4 sem | Control desde WhatsApp, Telegram, Discord, Slack |
| 7 | Sistema de Nodes | 4-5 sem | Dispositivos conectados como sensores y actuadores |
| 8 | Canvas + Skills + Cron | 4-5 sem | Dashboards, plugins y tareas automáticas |
| 9 | Tareas 24/7 + Presupuesto | 3-4 sem | Operación continua y gestión de recursos |
| 10 | Seguridad + RBAC + Políticas | 3-4 sem | Control de acceso, sandboxing y restricciones |
| 11 | Memoria Avanzada + Knowledge Graph | 4-5 sem | Contexto largo, grafo relacional del usuario |
| 12 | RPA + Macros + Grabación + Rollback | 3-4 sem | Automatización grabable y recuperación de errores |
| 13 | Analytics + DAG + Goal Engine | 4-5 sem | Planificación avanzada y medición de rendimiento |
| 14 | Bus de Eventos + Self-Healing + Versionado | 3-4 sem | Resiliencia y desacoplamiento de módulos |
| 15 | Módulos Especializados (ETL, Alertas, Costos, RLHF) | 4-5 sem | Inteligencia operativa avanzada |
| 16 | Agentes Autónomos Especializados | 4-5 sem | CFO, Negociador, SOP Generator, Árbitro, A/B Testing |
| 17 | Features de Productividad Avanzadas | 3-4 sem | Clipboard, Inbox unificada, File Manager, Proxy |
| 18 | Modo Offline + Sincronización + Pulido Final | 3-4 sem | Producto final completo y portable |

**Timeline Total Estimado: 62–82 semanas (~15–20 meses)**

---

## Fase 1 — Chat con todos los LLMs + UI Electron
**Duración estimada:** 3-4 semanas  
**Objetivo:** App funcional que permite chatear con cualquier modelo de IA (cloud + local)

**Referencia del documento:** §88 Fase 1, §78 Proveedores de IA, §83 UI Electron, §85 Comunicación

### Entregables
- [x] Estructura del proyecto (Electron + Python backend FastAPI)
- [x] WebSocket bidireccional Electron ↔ Python
- [x] Router de proveedores LLM:
  - OpenAI (GPT-4o, o1, o3)
  - Anthropic (Claude 3.5/3.7 Sonnet)
  - Google (Gemini 2.0 Flash, Gemini 2.5 Pro)
  - xAI (Grok 3, Grok Live Voice)
  - DeepSeek (V3, R1)
  - Mistral, Cohere, Perplexity
- [x] Soporte modelos locales (Ollama, LM Studio, Jan)
- [x] Frontend Electron: ventana principal + chat básico
- [x] Configuración de API keys y selección de modelo/proveedor
- [x] System tray icon + inicio con Windows configurable
- [ ] Empaquetado básico (.exe / NSIS installer)
- [x] Historial de conversaciones persistente

**✅ Entregable final:** Reemplaza ChatGPT desktop. Chat con cualquier modelo, local o cloud, desde una sola app.

---

## Fase 2 — Ver pantalla + hacer clicks *(CORE DIFERENCIADOR)*
**Duración estimada:** 4-5 semanas  
**Objetivo:** El agente puede ver y actuar sobre la pantalla completa del PC y dispositivos Android

**Referencia del documento:** §80 Sistema de Visión, §81 Automatización, §38 App Automator, §86 DPI

### Entregables

#### Visión
- [x] Captura de pantalla en tiempo real (mss) — <50ms
- [x] OCR multimotor: Tesseract + EasyOCR + PaddleOCR
- [x] Integración OmniParser de Microsoft (detección semántica de UI)
- [x] Modo Computer Use: envío de imagen completa al LLM
- [x] Modo Token Saver: solo envía texto OCR extraído
- [x] Preview en UI de lo que el agente está viendo
- [x] Detección de elementos clickables, botones, formularios

#### Automatización de Escritorio
- [x] PyAutoGUI: click, doble-click, right-click, scroll, drag & drop
- [x] pynput: hotkeys globales, listeners de teclado
- [x] Escritura de texto en campos activos
- [x] Manejo DPI + multi-monitor (SetProcessDpiAwareness)
- [x] Escalado de coordenadas por DPI y resolución

#### Loop del Agente (Computer Use)
- [x] Captura → OCR/Análisis → LLM → Acción → Verificación → Captura
- [x] Detección de éxito/fallo visual
- [x] Reintentos automáticos con estrategia alternativa
- [x] Controles en UI: ▶️ Start / ⏸ Pause / ⏹ Stop

#### Android (ADB / scrcpy)
- [x] Conexión ADB por USB y WiFi (pure-python-adb)
- [x] Tap, swipe, screenshot en dispositivo Android
- [x] Captura de pantalla del celular en tiempo real
- [x] OCR sobre pantalla de Android
- [x] Automatización de apps móviles

**✅ Entregable final:** Agente autónomo que puede operar cualquier app del PC y Android ejecutando tareas de principio a fin. El diferenciador clave de G-Mini.

---

## Fase 3 — Personaje animado + voz
**Duración estimada:** 4-5 semanas  
**Objetivo:** Asistente virtual animado que habla, escucha, y conversa en tiempo real

**Referencia del documento:** §82 Asistente Virtual, §53 Voice Pipeline, §83 UI Electron

### Entregables

#### Overlay del Personaje
- [x] Overlay Electron transparente (click-through durante automatización)
- [x] Animador de sprites 2D con 4 estados: `idle`, `talk`, `blink`, `blink_talk`
- [x] Importador de sprites 2D customizados (PNG/spritesheet)
- [ ] Renderer Three.js para modelos 3D (.glb / VRM)
- [x] Drag, resize del overlay
- [x] Hover buttons: 💬 Chat · 🎤 STT · 📞 Llamada · ⚙️ Config · ✖️ Cerrar
- [x] Modo minimizado a system tray

#### Síntesis de Voz (TTS)
- [x] MeloTTS offline (multi-idioma, zero-latency)
- [x] ElevenLabs online (clonación de voz del usuario)
- [x] Análisis RMS del audio para lipsync en tiempo real
- [x] Pipelining de audio: generación mientras habla
- [x] Pre-buffer: frases frecuentes pregeneradas

#### Speech-to-Text (STT)
- [x] Botón 🎤 activar Faster-Whisper local
- [x] Transcripción en tiempo real con baja latencia
- [x] Detección de silencio para envío automático

#### Voz Real-Time (Streaming)
- [x] Botón 📞 conversación bidireccional continua — `voiceRealtime.js` con captura PCM16 a 16 kHz vía `getUserMedia()` + `ScriptProcessorNode`, playback streaming, handlers `user:realtime_start/stop/audio` en websocket_handler.py, `AgentCore.start_realtime_voice()` / `send_realtime_audio()` / `stop_realtime_voice()`.
- [x] Soporte OpenAI Realtime API (WebSocket)
- [x] Soporte Gemini Live (streaming)
- [x] Soporte Grok Live Voice (xAI SDK)
- [x] Interrupción de respuesta al hablar el usuario

#### Configuración
- [x] Selector de personaje (sprite 2D / modelo 3D)
- [x] Selector de voz TTS
- [x] Ajuste de velocidad, tono y volumen
- [x] Posición y tamaño del overlay persistentes

**✅ Entregable final:** Asistente con personaje animado que habla, escucha y conversa en tiempo real. Experiencia inmersiva tipo compañero de IA.

---

## Fase 4 — Sistema de Modos + Sub-Agentes
**Duración estimada:** 4-5 semanas  
**Objetivo:** Múltiples personalidades especializadas y capacidad de trabajo paralelo multi-agente

**Referencia del documento:** §3 Modos, §4 Sub-Agentes, §5 Terminales, §96 Critic Agent

### Entregables

#### Sistema de Modos
- [x] Motor de modos con system prompts dinámicos
- [x] UI para cambiar de modo (dropdown + shortcut)
- [x] Modos predefinidos completos:
  - 🔧 Programador (código, Git, deploy, Docker)
  - 📈 Marketero (ads, redes sociales, campañas)
  - 💼 Asesor de Ventas (leads, seguimiento, cierre)
  - 🔍 Investigador + Perfilador (OSINT, perfiles, geopolítica)
  - 🕵️ Pentester Ético + Hacker (seguridad ofensiva, CTF)
  - 📚 Tutor/Coach (planes de estudio, seguimiento)
  - 👨‍👩‍👧 Padre Digital (productividad, límites, horarios)
  - 🎮 Gamer (automatización de juegos por visión)
  - 🎬 Creador de Contenido (video, thumbnails, clips IA)
  - 🤖 Normal (asistente general, modo default)
- [x] Sistema de modos personalizados (YAML con prompt + permisos)
- [x] Persistencia de modo por sesión

#### Sistema de Sub-Agentes
- [x] Arquitectura multi-agente (orquestador + workers)
- [x] Spawn y ciclo de vida de sub-agentes
- [x] Comunicación bidireccional: principal ↔ sub-agentes
- [x] Panel de monitoreo de sub-agentes activos en UI
  - Estado, tarea actual, tiempo transcurrido, tokens usados
- [x] Límites configurables: máx. 5 sub-agentes simultáneos
- [x] Herencia de permisos con restricciones adicionales
- [x] Consolidación de resultados por el orquestador

#### Critic Agent (§96)
- [x] Sub-agente revisor previo a acciones sensibles
- [x] Score de confianza 0–1 por tipo de acción
- [x] Tabla de umbrales: lectura 0.55 · archivos 0.75 · publicaciones 0.85 · pagos 0.95
- [x] Dry-run automático cuando el score está bajo el umbral
- [x] Escalación a humano cuando no hay confianza suficiente

#### Multi-Shell (§5)
- [x] Detección automática de terminales disponibles (PowerShell, CMD, Git Bash, WSL)
- [x] Selección inteligente de terminal por tipo de tarea
- [x] Hasta 10 terminales simultáneas activas
- [x] Panel de terminales activas en UI

**✅ Entregable final:** Agente con 10+ personalidades especializadas y capacidad de delegar tareas a sub-agentes que trabajan en paralelo.

---

## Fase 5 — Integraciones Externas
**Duración estimada:** 3-4 semanas  
**Objetivo:** Agente conectado al ecosistema completo de herramientas del usuario

**Referencia del documento:** §6 Chrome, §7 APIs Externas, §33 Email, §43 Redes Sociales, §65 E-commerce, §72 Ventas B2B

### Entregables

#### Control de Navegador (§6)
- [x] Extensión Chrome (Content Script + Background Service Worker)
- [x] WebSocket extensión ↔ backend (puerto 8765)
- [x] Comandos: navigate, click, type, screenshot, get_dom, execute_script
- [x] Soporte multi-perfil de Chrome (cada perfil con su extensión)
- [x] Preservación de sesiones, cookies y logins existentes

#### APIs de Redes Sociales (§43)
- [ ] Facebook: publicaciones, grupos, ads (API Graph)
- [ ] Instagram: publicaciones, stories, reels (API Graph)
- [x] X/Twitter: tweets, hilos, DMs (API v2)
- [ ] TikTok: subida de videos, gestión de cuenta
- [x] LinkedIn: publicaciones, mensajes, conexiones
- [x] YouTube: subida, descripción, thumbnails (YouTube Data API)
- [ ] Gestión multi-cuenta por plataforma

#### Integración de Herramientas Creativas
- [ ] CapCut: control automatizado vía UI (§80 Visión)
- [x] ffmpeg: edición de video por comandos
- [ ] Canva: creación de diseños vía API y UI
- [ ] OBS Studio: grabación y streaming

#### APIs de IA Generativa
- [x] ElevenLabs: clonación de voz, TTS premium (§53)
- [ ] Runway / Kling: generación de video con IA (§61)
- [x] DALL-E / Stable Diffusion / Flux: generación de imágenes (§61)
- [ ] Midjourney: generación vía Discord bot

#### Conectores de Productividad (§7)
- [ ] Notion: leer/escribir páginas y bases de datos
- [x] Google Calendar: eventos, recordatorios, disponibilidad
- [x] Google Sheets/Drive: lectura y escritura
- [x] Slack: mensajes, canales, workflows
- [ ] Airtable: bases de datos
- [ ] HubSpot / Salesforce / Pipedrive: CRM (§65, §72)

#### Email Inteligente (§33)
- [x] Gmail / Outlook: leer, redactar, responder, clasificar
- [x] Auto-responder con reglas configurables
- [x] Composer de emails por contexto del hilo
- [x] Seguimiento automático si no hay respuesta

**✅ Entregable final:** Agente conectado a toda la suite de herramientas del usuario: redes sociales, CRM, email, diseño, y APIs de IA generativa.

---

## Fase 6 — Gateway Multi-Canal
**Duración estimada:** 3-4 semanas  
**Objetivo:** Control del agente desde múltiples plataformas de mensajería

**Referencia del documento:** §8 Gateway Multi-Canal

### Entregables

#### Arquitectura del Gateway
- [x] Router de sesiones base: outbox persistente + sesiones locales por canal
  Base operativa ya disponible: `GatewayService` con `gateway_sessions` y `gateway_outbox` persistentes en SQLite, entrega en vivo a la app local por Socket.IO y flush de pendientes al reconectar.
- [x] Sesión `main` (chat directo), sesiones por grupo por canal
  Base operativa disponible para `local_app:main`; el modelo de sesión ya existe y queda listo para extenderse a grupos/canales externos.
- [ ] Manejo de adjuntos: imágenes, PDFs, audio, video
- [x] Sistema de confirmación remota para acciones críticas
  Base operativa ya disponible en Telegram, WhatsApp y Discord: las aprobaciones pendientes viajan por Gateway, incluyen token por solicitud y pueden resolverse desde el canal remoto. Telegram ya soporta botones inline; WhatsApp y Discord operan con comandos tokenizados.

  Nota de estado: ya existe base parcial de adjuntos en Telegram con recepcion de imagenes/documentos, descarga local y screenshots del agente enviados como foto. WhatsApp Web ya soporta base operativa de screenshots salientes y adjuntos basicos de imagen/documento hacia y desde el agente. Siguen pendientes PDFs/audio/video y manejo avanzado multi-canal.

#### Bots por Canal
- [x] **WhatsApp Web:** base operativa de recibir/enviar mensajes por `whatsapp-web.js` vía subprocess Node
  Base operativa ya disponible: bridge Node por stdio con sesión persistente por QR, runtime visible desde Settings, envío saliente de texto e imagen/documento por outbox del Gateway, screenshots del agente por el mismo canal, ruteo de mensajes/adjuntos entrantes al `AgentCore`, comandos remotos por chat (`/estado`, `/start`, `/pause`, `/stop`, `/aprobar`, `/cancelar`, `/modo`) y activación por alias configurable en grupos.
  - Comandos de control: `/modo`, `/pausa`, `/stop`, `/estado`
  - Recibir screenshots del agente en tiempo real
  - Aprobar/rechazar acciones críticas con 👍/👎
- [x] **Telegram:** bot operativo por polling con sesiones remotas, confirmaciones y adjuntos base
  - Base operativa ya disponible: token en vault, long polling, outbox saliente, sesiones `main/private/group` por chat, comandos `/estado`, `/start`, `/pause`, `/stop`, `/aprobar`, `/cancelar`, `/modo`, activación por mención/alias en grupos y ruteo de texto al `AgentCore`.
  - Actualizacion: ya soporta screenshots salientes y adjuntos de imagen/documento entrantes en Telegram como base funcional.
  - Actualizacion: ya soporta botones inline basicos para aprobar/cancelar y controles remotos de estado/pausa/reanudar/stop por callback.
  - Actualizacion: las aprobaciones remotas ahora viajan con token por solicitud para evitar taps viejos o cruzados desde mensajes anteriores.
- [x] **Discord:** bot base operativo por `discord.py`
  - Base operativa ya disponible: token en vault, runtime visible desde Settings, sesiones remotas por canal/DM, comandos `/estado`, `/start`, `/pause`, `/stop`, `/aprobar`, `/cancelar`, `/modo`, activación por mención/alias en servidores y adjuntos básicos hacia el `AgentCore`.
  - Pendiente: thread por tarea larga y respuestas ricas tipo botones/modales.
- [x] **Slack:** integración (slack-sdk)
  - App Slack con comandos slash
  - Notificaciones en canales configurados
  - Modal de confirmación de acciones

#### Control Remoto
- [x] Activar/pausar/detener el agente desde Telegram/WhatsApp/Discord
  Base operativa ya disponible: `/start`, `/pause` y `/stop` controlan el runtime actual del agente desde chats/canales autorizados.
- [x] Ver estado de tareas activas desde Telegram/WhatsApp/Discord
  Base operativa ya disponible: `/estado` devuelve runtime, modo, modelo y si hay aprobación pendiente en sesiones remotas autorizadas.
- [x] Recibir notificaciones push de completado/error
  Base operativa ya disponible en `local_app`, `telegram`, `whatsapp` y `discord`: el scheduler notifica completado/error al gateway y el mensaje se entrega en vivo o desde outbox al reconectar.
- [x] Cambiar modo del agente remotamente en Telegram/WhatsApp/Discord
  Base operativa ya disponible por sesión remota con `/modo <nombre>` sin pisar el modo global de la app local.
- [x] Activación por mención en grupos
  Base operativa ya disponible en Telegram, WhatsApp y Discord: en grupos/servidores el agente solo procesa comandos directos o mensajes que incluyan mención/alias configurados, evitando reaccionar al ruido general del canal.

**✅ Entregable final:** Agente controlable desde el celular vía WhatsApp, Telegram, Discord y Slack. Control total en movimiento.

---

## Fase 7 — Sistema de Nodes (Dispositivos Conectados)
**Duración estimada:** 4-5 semanas  
**Objetivo:** Dispositivos móviles y PCs remotas como extensiones del agente

**Referencia del documento:** §9 Nodes, §31 Multi-PC, §32 Smart Home / IoT

### Entregables

#### Arquitectura de Nodes
- [x] Protocolo WebSocket de emparejamiento seguro (token de un uso)
- [x] Sistema de superficies: `camera.*`, `location.*`, `files.*`, `exec.*`, etc.
- [x] Permisos granulares por superficie y por node
- [x] Panel de nodes conectados en UI principal

#### App Companion Mobile
- [ ] **iOS:** cámara en vivo, GPS, notificaciones push, microfono, voz
- [ ] **Android:** cámara, GPS, SMS, contactos, info del dispositivo, notificaciones
- [ ] Streaming de cámara al agente para visión remota
- [ ] Ejecutar comandos de automatización en el móvil desde la PC

#### Node de PC Remota (§31)
- [ ] Agente ligero instalable en cualquier Windows/Linux/Mac
- [ ] Superficies: `system.*`, `exec.*`, `files.*`, `screen.*`
- [x] Lista blanca de comandos permitidos (exec approvals)
- [ ] Sincronización de archivos entre PCs

#### Smart Home / IoT (§32)
- [x] Bridge con Home Assistant (HTTP API)
- [x] Control de dispositivos: luces, enchufes, termostatos, cámaras
- [x] Automatizaciones con lenguaje natural: "Apaga las luces a las 10pm"
- [x] Estado del hogar accesible desde cualquier canal del Gateway

**✅ Entregable final:** Red de dispositivos bajo el control del agente. Celular como sensor, PCs remotas como ejecutores, y casa inteligente integrada.

---

## Fase 8 — Canvas + Skills + Cron
**Duración estimada:** 4-5 semanas  
**Objetivo:** Dashboards visuales en tiempo real, sistema de plugins y tareas programadas

**Referencia del documento:** §10 Canvas, §11 Skills, §12 Cron, §13 Background Jobs

### Entregables

#### Canvas (§10)
- [x] Motor de Canvas: renderizado HTML/Jinja2 actualizable en tiempo real
- [x] Tipos de canvas: estado, dashboard, monitor, lista, tabla, custom
- [x] API para que el agente actualice un canvas desde cualquier tarea
- [ ] Canvas en nodes: renderizar dashboard en dispositivos remotos
- [ ] Historial de versiones de canvas

#### Sistema de Skills / Plugins (§11)
- [x] Base de configuración para skills y servidores MCP desde Settings
- [x] Descubrimiento local de skills con prioridad workspace → custom → local → bundled
- [x] Validación e inspección de servidores MCP configurados
- [x] Runtime base para servidores MCP `stdio` configurados (`initialize` + `tools/list` + `tools/call`)
- [x] Instalación local de skills desde carpeta o repo Git
- [x] Habilitar, deshabilitar y desinstalar skills locales
- [ ] Registry de skills (local + remoto)
- [ ] Instalación desde registro oficial o Git repo
- [x] Estructura base de skill: `skill.yaml` + `README.md` + `tools/*.py` o script/entrypoint declarado
- [x] Prioridad real implementada: workspace → custom → local → bundled
- [x] Runtime base de ejecución aislada de skills (subprocess sin shell, timeout, env reducido y contrato JSON)
- [ ] Skills bundled incluidas:
  - `web_search` (Tavily / SearXNG)
  - `code_executor` (Python sandbox)
  - `file_manager` (lectura/escritura/búsqueda)
    Skill bundled base ya incluida: `file-manager::inspect_text_file`.
    Base interna ya disponible en el core: `workspace_snapshot`, `git_status`, `git_changed_files`, `git_diff`, `git_log`, `code_outline`, `code_related_files`, `file_list`, `file_read_text`, `file_read_batch`, `file_search_text`, `file_replace_text`, `file_write_text`, `file_exists`.
    Base nativa en la app ya iniciada: panel de workspace/codigo en Electron con snapshot del proyecto, cambios Git, explorador de archivos y visor de archivo conectado al chat.
  - `browser_control` (Chrome extension bridge)
  - `ide_control` (VS Code / Cursor)
    Base interna ya disponible en el core: `ide_detect`, `ide_open_workspace`, `ide_open_file`, `ide_open_diff`, `ide_state`, `ide_active_file`, `ide_selection`, `ide_workspace_folders`, `ide_diagnostics`, `ide_symbols`, `ide_find_symbol`, `ide_reveal_symbol`, `ide_reveal_range`, `ide_open_diagnostic`, `ide_next_diagnostic`, `ide_prev_diagnostic`, `ide_apply_edit`, `ide_apply_workspace_edits`, mas extension local en `assets/vscode-bridge/`.
  - `image_generator` (Stable Diffusion / DALL-E)

#### Cron y Scheduler (§12)
- [x] Triggers base: cron expression e intervalo
- [x] Triggers pendientes: heartbeat, evento, webhook
- [x] Parser de expresiones cron (croniter)
- [x] Panel de tareas programadas en UI
- [x] API + planner para crear, listar, actualizar, ejecutar y eliminar jobs programados
- [x] Historial de ejecuciones (éxito/fallo/duración)
- [x] Reintentos automáticos con backoff
  Base persistente ya implementada en SQLite para jobs `skill` y `mcp_tool`, con scheduler en backend, endpoints REST, acciones `schedule_*` en el planner, política de retries con `max_retries`, backoff base, multiplicador y seguimiento de `retry_attempt`, además de triggers reales `heartbeat`, `event` y `webhook` con payload de señal inyectado en `_trigger`.

**✅ Entregable final:** Dashboards vivos que se actualizan solos, marketplace de plugins extensibles, y motor de automatización recurrente.

---

## Fase 9 — Tareas 24/7 + Presupuesto
**Duración estimada:** 3-4 semanas  
**Objetivo:** Operación continua sin supervisión y control del gasto

**Referencia del documento:** §13 Background Jobs, §14 Presupuesto, §114 Monitor de Costos

### Entregables

#### Background Jobs y Checkpoints (§13)
- [x] Sistema de checkpoints en disco (SQLite) para tareas largas
  Base operativa ya disponible: `scheduled_checkpoints` persistentes con progreso, tipo, mensaje y payload por run/job, accesibles desde API y planner.
- [x] Recuperación automática tras reinicio o crash del sistema
  Base operativa ya disponible: runs que quedaron en estado `running` se marcan como `interrupted` al iniciar, se registran checkpoints de recovery y el scheduler reprograma retry o próxima ejecución según la política del job.
- [x] Background jobs persistentes (sobreviven cierre de ventana)
  Base operativa ya disponible: close-to-tray / minimize-to-tray / start-hidden-to-tray configurables en la app, manteniendo scheduler y backend vivos mientras la ventana está oculta.
- [x] Panel de tareas 24/7 en UI con estado, progreso y logs
  Base operativa ya disponible: panel nativo del scheduler dentro de G-Mini con resumen 24/7, estado del job seleccionado, historial de runs y checkpoints/logs persistentes visibles desde Electron.
- [x] Notificación por Gateway al completar o fallar
  Base operativa ya disponible para `local_app`, `telegram`, `whatsapp` y `discord` con outbox persistente, sesiones activas y entrega/reintento al reconectar. Slack sigue pendiente.

#### Monitor de Costos en Tiempo Real (§114)
- [x] Contador de tokens (entrada + salida) por tarea activa
- [x] Conversión automática a USD por proveedor/modelo configurable
- [x] Dashboard de costos en UI: sesión actual, acumulado hoy, acumulado mensual
- [x] Alertas preventivas antes de exceder presupuesto
- [x] Pausa automática de tarea si se supera el techo

#### Sistema de Presupuesto (§14)
- [x] Configuración de presupuesto global mensual en USD
- [x] Presupuesto por modo y por tarea individual
- [x] Límite por sub-agente (hereda del §4)
- [x] Registro de cuentas y tarjetas con límites de gasto
- [x] Permisos de gasto: `ask_always`, `ask_above_X`, `auto_approve_under_X`
- [x] Reporte de gasto semanal enviado por Gateway — `CostTracker.send_weekly_report_to_gateway()` implementado end-to-end; cron job `budget_weekly_report` auto-creado en `main.py` (lunes 9am UTC); dispatch en `scheduler.py`; entrega vía `GatewayService.send_text_notification()` a todos los targets configurados en `weekly_report_gateway_targets`.

Estado real actual:
- Ledger SQLite de uso LLM con eventos por sesión y resumen sesión/hoy/mes.
- Tabla de precios editable por proveedor/modelo en YAML, con defaults iniciales ajustables.
- Dashboard nativo en Electron y Settings para límites diario, mensual, warning, por tarea, por modo y por sub-agente.
- Política configurable de gasto/pagos con `deny_all`, `ask_always`, `ask_above_x` y `auto_approve_under_x`, aplicada desde `PolicyEngine` y visible en la tarjeta de aprobación.
- Registro normalizado de cuentas/tarjetas con `default_account_id`, límites por cuenta y enforcement básico por `account_id` o `payment_account_id`.
- Reporte semanal operativo disponible desde `CostTracker`, API, planner y panel nativo, con comparativa vs semana previa, breakdown por proveedor/modo/worker y `weekly_report_gateway_targets` listos para futura entrega por Gateway.
- Gateway base operativo con sesiones locales `local_app`, outbox persistente y endpoints/API/planner para inspección y envío de notificaciones (`gateway_status`, `gateway_list_sessions`, `gateway_list_outbox`, `gateway_notify`).
- Gateway extendido con conectores externos reales: Telegram con token en vault, polling, sesiones remotas por chat, comandos básicos, adjuntos base, inline approvals y activación por mención/alias en grupos; WhatsApp Web con bridge Node, QR/runtime en Settings, texto bidireccional base, comandos remotos, activación por alias en grupos, screenshots salientes y adjuntos básicos por sesión remota; y Discord con bot `discord.py`, token en vault, runtime en Settings, sesiones remotas por canal/DM, comandos remotos, activación por mención/alias y adjuntos básicos hacia el agente.

#### Optimización Automática de Costos (§114.4)
- [x] Auto-switch a modelo más económico cuando la tarea lo permite
  Base operativa ya implementada: `CostOptimizer` en `backend/core/cost_optimizer.py` con clasificación de criticidad por fuente/modo, evaluación de presión presupuestaria (none/low/medium/high/exceeded), cadena de downgrade configurable en YAML, selección automática de modelo más económico según presión y criticidad de la tarea, y metadatos de optimización en cada evento de uso LLM. Integrado en `ModelRouter.generate_cost_aware()` y `generate_complete_cost_aware()` para routing transparente. Tres endpoints REST (`/costs/optimizer/status`, `/costs/optimizer/pressure`, `/costs/optimizer/invalidate`) y dos acciones de planner (`cost_optimizer_status`, `cost_optimizer_pressure`).
- [x] Compresión de contexto antes de llamadas costosas (§104)
  Base operativa ya implementada: `AgentCore._compress_messages_for_cost()` comprime mensajes cuando la presión presupuestaria es media o alta y los tokens de entrada superan el umbral configurable (`compress_context_above_tokens`, default 40k). Mantiene system prompt, últimos N mensajes recientes y resumen compacto de mensajes antiguos.
- [x] Priorizar modelos locales en tareas no críticas
  Base operativa ya implementada: `CostOptimizer` prioriza `local_fallback_provider` (Ollama/LM Studio) para tareas de criticidad `low` (delegación, compresión, clasificación, extractores) cuando la presión presupuestaria es alta o excedida. Configurable en `cost_optimization.local_fallback_provider` y `local_fallback_model`.

**✅ Entregable final:** Agente que opera 24/7 sin supervisión, con checkpoints que previenen pérdida de progreso, y control total del gasto en tokens y dinero.

---

## Fase 10 — Seguridad + RBAC + Políticas
**Duración estimada:** 3-4 semanas  
**Objetivo:** Control de acceso granular, sandboxing y cumplimiento de restricciones éticas

**Referencia del documento:** §15 Restricciones Éticas, §87 Seguridad, §94 RBAC, §105 Prompt Injection

### Entregables

#### Motor de Políticas Unificado + RBAC (§94)
- [x] Definición declarativa de roles: Owner, Operator, Approver, Auditor, Viewer
- [x] Políticas YAML por usuario, sesión, modo, skill y entorno
- [x] Precedencia: Hard restrictions > Deny explícito > Condicional > Allow > Default deny
- [x] Solicitud de aprobación en tiempo real (via Gateway) para acciones condicionales
- [x] Admin panel de roles y políticas en UI

#### Sandbox y Ejecución Aislada (§87)
- [x] Docker sandbox para ejecución de código no confiable
- [x] Timeout y límites de recursos por sandbox
- [x] Lista blanca/negra de herramientas accesibles
- [x] Logging de todas las acciones ejecutadas en sandbox

#### Restricciones Éticas Hardcodeadas (§15)
- [x] Lista inmutable de acciones siempre prohibidas (no configurables):
  - Acceso a sistemas sin autorización del dueño
  - Recopilación de datos de menores
  - Manipulación psicológica maliciosa
  - Destrucción masiva de datos sin confirmación explícita
  - Bypass de medidas de seguridad propias del agente
- [x] Restricciones configurables por usuario (capa por encima de las hardcodeadas)
- [x] Modo pentester: activación explicit con confirmación de scope

#### Detección de Prompt Injection (§105)
- [x] Separación estricta contexto del sistema / datos externos
- [x] Contenido leído de web, PDFs, emails clasificado como UNTRUSTED
- [x] Scanner de patrones de injection en contenido externo
- [x] Alerta y bloqueo cuando se detecta instrucción maliciosa embebida
- [x] Niveles de confianza: TRUSTED (usuario) > SYSTEM > ELEVATED (archivos aprobados) > UNTRUSTED (externos)

#### Logging y Auditoría
- [x] Log completo de acciones críticas con timestamp, actor, resultado
- [x] Exportación de logs en JSON/CSV para auditoría externa
- [x] Dashboard de auditoría (Rol: Auditor)
- [x] Retención configurable de logs

**✅ Entregable final:** Sistema de permisos y seguridad de nivel empresarial, con sandbox para código, protección contra prompt injection y restricciones éticas no negociables.

---

## Fase 11 — Memoria Avanzada + Knowledge Graph
**Duración estimada:** 4-5 semanas  
**Objetivo:** El agente recuerda todo sobre el usuario, mantiene contexto en conversaciones largas y razona sobre relaciones

**Referencia del documento:** §16 Memoria, §104 Contexto Largo, §112 Knowledge Graph

### Entregables

#### Memoria a Largo Plazo (§16)
- [x] Almacén de memoria persistente (SQLite + embeddings)
- [x] Categorías: hechos del usuario, preferencias, historial de tareas, aprendizajes
- [x] Búsqueda semántica (RAG) sobre la memoria
- [x] Inyección automática de contexto relevante al inicio de cada conversación
- [x] Interfaz para que el usuario vea, edite y borre su memoria
- [x] Expiración y priorización de memorias por uso

#### Compresión de Sesión Larga (§104)
- [x] Trigger automático al alcanzar 80k tokens en contexto
- [x] Generación de mapa de tarea persistente (JSON estructurado)
- [x] Preservación de: objetivo original, hechos clave, decisiones tomadas, tareas pendientes
- [x] Compresión de historial antiguo en resumen embedding
- [x] Reconstrucción transparente al retomar sesión anterior:
  > *"[Contexto restaurado] Continuamos con... ¿Seguimos?"*

#### Knowledge Graph del Usuario (§112)
- [x] Backend: NetworkX (local, sin dependencias) o Neo4j (avanzado)
- [x] Entidades: Personas, Empresas, Proyectos, Productos, Eventos, Tareas
- [x] Relaciones: trabaja_en, es_cliente_de, compite_con, asignado_a, depende_de, interesado_en
- [x] Construcción automática del grafo desde conversaciones y tareas
- [x] Consultas de razonamiento relacional:
  - *"¿Quién puede reemplazar a Juan si no responde?"*
  - *"¿Qué clientes se ven afectados si Acme cancela?"*
- [x] Resolución de conflictos: `latest_wins_with_audit`
- [ ] Visualización del grafo en UI (Canvas)

**✅ Entregable final:** Agente que recuerda absolutamente todo, mantiene coherencia en conversaciones de horas, y razona sobre relaciones complejas del universo del usuario.

---

## Fase 12 — RPA + Macros + Grabación + Rollback
**Duración estimada:** 3-4 semanas  
**Objetivo:** Automatización grabable, reproducible y reversible

**Referencia del documento:** §17 Grabación de Pantalla, §18 Macros/RPA, §19 Rollback

### Entregables

#### Grabación de Pantalla y Replay (§17)
- [ ] Grabación continua de pantalla en background (buffer circular)
- [ ] Guardado de clips al detectar errores o a petición
- [ ] Replay de sesiones pasadas para diagnóstico
- [ ] Compresión automática de grabaciones antiguas

#### Macros y Workflows Grabables (§18)
- [x] Modo de grabación: el agente observa las acciones del usuario y las aprende
- [x] Conversión de grabación a workflow ejecutable (YAML/JSON)
- [ ] Editor visual de macros en UI
- [x] Exportar/importar macros entre instancias
- [x] Ejecución de macros por trigger (cron, evento, comando)
- [x] Parametrización de macros (variables dinámicas)

#### Sistema de Rollback / Undo (§19)
- [x] Snapshot del estado del sistema antes de acciones críticas
  - Archivos afectados (copia antes de modificar)
  - Estado de aplicaciones (URLs, pestañas abiertas)
  - Comandos ejecutados (log reversible)
- [x] Rollback de hasta los últimos 10 snapshots
- [x] Confirmación explícita antes de acciones destructivas irreversibles
- [x] Log de rollbacks ejecutados

**✅ Entregable final:** Agente que aprende viéndote trabajar, convierte eso en macros reutilizables y puede deshacer cualquier acción que salió mal.

---

## Fase 13 — Analytics + DAG Planner + Goal Engine
**Duración estimada:** 4-5 semanas  
**Objetivo:** Planificación avanzada de tareas complejas, objetivos de largo plazo y medición del rendimiento

**Referencia del documento:** §20 Analytics, §95 DAG, §100 Goal Engine, §128 Dashboard Ejecutivo

### Entregables

#### Planificador DAG (§95)
- [x] Modelo de ejecución de tareas con dependencias explícitas (Directed Acyclic Graph)
- [x] Ejecución paralela de ramas independientes
- [x] Reintentos con backoff configurable por nodo
- [x] Skip/control de ramas opcionales
- [x] Reanudación desde checkpoint del DAG tras fallo
- [ ] Visualización del DAG en UI con estado de cada nodo

#### Sistema de Objetivos Persistentes / Goal Engine (§100)
- [x] Estructura de objetivo: id, título, métrica de éxito, deadline, sub-tareas
- [x] Descomposición automática de objetivos en DAGs de tareas
- [x] Medición automática de progreso (KPI tracking)
- [x] Replanificación cuando hay desviaciones del objetivo
- [x] Objetivos de largo plazo que persisten entre sesiones
- [x] Dashboard de objetivos activos con progreso en tiempo real

#### Analytics del Agente (§20)
- [x] Métricas de rendimiento: tareas completadas, tasa de éxito, tiempo promedio
- [x] Uso de tokens por proveedor y por modo
- [x] Distribución de tiempo por tipo de tarea
- [x] Historial de errores y causas
- [x] Reportes semanales automáticos

#### Dashboard Ejecutivo (§128)
- [x] Vista consolidada: tareas activas, objetivos, costos, alertas
- [x] Línea de tiempo de actividad del agente (últimas 24h / 7d / 30d)
- [x] Acceso rápido a logs de cualquier tarea
- [x] Notificaciones y acciones pendientes de aprobación

**✅ Entregable final:** Agente que no solo ejecuta tareas, sino que persigue objetivos de semanas y meses, descomponiéndolos en pasos ejecutables y midiendo el progreso continuamente.

---

## Fase 14 — Bus de Eventos + Self-Healing + Versionado
**Duración estimada:** 3-4 semanas  
**Objetivo:** Arquitectura robusta, resiliente y mantenible

**Referencia del documento:** §97 Bus de Eventos, §98 Self-Healing, §99 Versionado

### Entregables

#### Bus de Eventos Central (§97)
- [x] Event Bus interno que unifica: gateway, cron, webhooks, nodes, skills, core
- [x] Contrato de evento: `event_id`, `type`, `source`, `timestamp`, `payload`, `session_id`
- [x] Sistema pub/sub: módulos suscriben a tipos de eventos
- [x] Cola persistente (SQLite): eventos no procesados sobreviven reinicios
- [x] Auditoría end-to-end de eventos (trazabilidad completa)
- [x] Sistema de webhooks entrantes (§56): cualquier servicio externo puede disparar eventos

#### Capa Anti-Frágil / Self-Healing (§98)
- [x] Recuperación automática de fallos comunes:
  - Selector no encontrado → retry con visión + búsqueda semántica
  - Timeout de página → refresh + esperar red
  - Ventana perdida → re-enfocar app
  - Tool error transitorio → retry con backoff exponencial
  - Provider IA caído → failover automático a proveedor alternativo (§78)
- [x] Guardrails de bucle infinito: `max_retries_per_step: 3`
- [x] Tiempo máximo por paso: configurable
- [x] `on_exhaustion`: `handoff` (al usuario) | `pause` | `cancel`

#### Integración con Zapier / Make / n8n (§57)
- [x] Webhook listener para recibir triggers de automatización externa
- [x] Exposición de acciones del agente como endpoints REST para n8n/Make
- [ ] Autenticación por API key para llamadas externas

#### Versionado de Artefactos (§99)
- [x] Workflows y macros: versionado en stages `draft → staging → prod`
- [x] Prompts de sistema por modo: historial completo de cambios
- [x] Políticas RBAC: auditoría de cada cambio (quién, cuándo, qué)
- [x] Configuración de router de modelos: rollback si nueva config falla
- [x] Retención de hasta 50 versiones por artefacto

**✅ Entregable final:** Sistema que se recupera solo de fallos, desacopla módulos con eventos, y tiene historial completo de cada cambio para auditoría y rollback.

---

## Fase 15 — Módulos Especializados (ETL, Alertas, Costos, RLHF)
**Duración estimada:** 4-5 semanas  
**Objetivo:** Inteligencia operativa avanzada: datos, alertas causales, dependencias y aprendizaje adaptativo

**Referencia del documento:** §110 ETL, §111 Alertas Causales, §113 Self-Healing Entorno, §121 RLHF

### Entregables

#### Pipeline de Datos ETL (§110)
- [x] Extracción desde: Google Sheets, Excel, Airtable, PostgreSQL, MySQL, SQLite, Shopify, HubSpot, Salesforce, CSV/JSON/XML, APIs REST
- [x] Transformaciones: filtrado, mapeo, validación, normalización, enriquecimiento
- [x] Carga en: Supabase, Google Sheets, bases de datos, archivos
- [ ] Joins multi-fuente (heterogéneas) en memoria con pandas/polars
- [x] Definición de pipelines en YAML
- [x] Ejecución programada via Cron (§12)

#### Motor de Alertas Causales (§111)
- [x] Monitoreo de métricas de negocio en tiempo real
- [x] Correlación temporal entre eventos para detectar causas raíz
- [x] Cálculo de impacto económico estimado
- [x] Acción automática cuando se detecta la causa (si la confianza ≥ 0.85)
- [x] Notificación al usuario con análisis completo:
  - Síntoma detectado
  - Causa raíz identificada
  - Impacto estimado
  - Acción tomada
  - Nivel de confianza

#### Gestión de Dependencias (Self-Healing de Entorno) (§113)
- [ ] Monitor de dependencias Python del agente
- [ ] Reparación automática de fallos de import
- [ ] Detección y resolución de conflictos de versiones
- [ ] Reconstrucción de venv si está corrompido
- [ ] Escaneo semanal de vulnerabilidades (CVEs) en dependencias
- [ ] Actualizaciones automáticas de patch seguro

#### Sistema de Recompensas / RLHF Ligero (§121)
- [x] Captura de señales implícitas: el usuario copia sin editar (+0.6), reescribe la petición (-0.5)
- [x] Captura de señales explícitas: 👍 (+0.9), "perfecto" (+1.0), regenera (-0.8), deshace acción (-1.0)
- [x] Almacén de preferencias por usuario (JSON persistente)
- [x] Inyección de preferencias aprendidas en el system prompt (context prefix)
- [x] Interfaz transparente: el usuario puede ver y editar lo aprendido
  > *"He aprendido que prefieres respuestas concisas (82%), ver código siempre (94%)..."*
- [x] 847+ señales procesadas = perfil de preferencias estable

**✅ Entregable final:** Agente que extrae y transforma datos entre cualquier fuente, detecta causas raíz de problemas del negocio, se mantiene solo y se vuelve progresivamente más personalizado.

---

## Fase 16 — Agentes Autónomos Especializados
**Duración estimada:** 4-5 semanas  
**Objetivo:** Sub-agentes verticales que resuelven dominios completos de forma autónoma

**Referencia del documento:** §116 Negociador, §117 SOP Generator, §118 Árbitro, §119 A/B Testing, §120 What-If, §122 CFO Virtual

### Entregables

#### Agente de Negociación Autónoma (§116)
- [x] Casos: renovar SaaS, negociar precio con proveedor, pedir cotizaciones, resolver disputas, obtener descuentos
- [x] Mandato configurable: límites de precio, plazo, condiciones mínimas aceptables
- [x] Estrategia multi-turno:
  1. Investigar mercado y precio de referencia
  2. Contactar proveedor (email/chat)
  3. Presentar propuesta inicial
  4. Contraofertar dentro del mandato
  5. Escalar al humano si no hay acuerdo
- [x] Log auditable de cada turno de negociación

#### Generador de Documentación Viva / SOP (§117)
- [x] Detección de tareas repetidas (≥3 ejecuciones similares)
- [x] Generación automática de SOP (Procedimiento Operativo Estándar) en Markdown
- [x] Incluye: objetivo, pre-requisitos, pasos, variantes detectadas, tiempo promedio
- [x] Actualización automática cuando el proceso evoluciona
- [x] Notificación al usuario cuando detecta cambio en el proceso:
  > *"En las últimas 5 veces... ¿Actualizo el SOP?"*
- [x] Formatos disponibles: SOP, wiki, video script, checklist, README

#### Árbitro de Conflictos entre Agentes (§118)
- [x] Resolución de conflictos de recurso compartido (lock FIFO)
- [x] Cola con backoff para rate limits de API compartidos
- [x] Escalación al usuario ante decisiones contradictorias (publicar vs no publicar)
- [x] Tabla de prioridades de tareas (hereda de §94 RBAC)
- [x] Solo un agente controla UI/ratón a la vez (mutex de pantalla)
- [x] Deadlock detection y resolución automática
- [x] **Métricas objetivo:** >90% sin intervención humana, <200ms resolución, 100% deadlocks resueltos

#### A/B Testing del Agente (§119)
- [x] Elementos testeables: tono de respuesta, estructura de informe, estrategia de planificación, threshold de autonomía
- [x] Configuración de experimento: control/variante, grupo de muestra, métricas, duración, confianza requerida
- [x] Motor estadístico: p-value, intervalo de confianza, n mínimo
- [x] Adopción automática del ganador al alcanzar significancia estadística
- [x] Notificación con resultados y acción tomada

#### Motor de Simulación What-If (§120)
- [x] Simulaciones: pricing, contratación, campaña publicitaria, churn, operaciones
- [x] Escenarios: optimista (P90), base (P50), pesimista (P10)
- [x] Intervalos de confianza en todos los resultados
- [x] Reporte visual con recomendación accionable
- [x] **Sandbox de datos:** las simulaciones nunca modifican datos reales
- [x] Ejecución real solo con aprobación explícita en paso separado

#### CFO Virtual / Agente Financiero (§122)
- [ ] P&L en tiempo real (ingresos − costos = beneficio) desde fuentes conectadas
- [ ] Proyección de flujo de caja semana a semana
- [ ] Cálculo de runway: *"A este ritmo, tienes dinero para X meses"*
- [ ] Análisis de contratación: *"¿Puedo permitirme este gasto?"*
- [ ] Detección de fugas: suscripciones olvidadas, gastos anómalos
- [ ] Proyecciones 3/6/12 meses: optimista, base, pesimista
- [ ] Integrado con ETL (§110) y Dashboard Ejecutivo (§128)

**✅ Entregable final:** Suite de agentes autónomos que pueden negociar contratos, documentar procesos, simular decisiones de negocio y actuar como CFO del usuario.

---

## Fase 17 — Features de Productividad Avanzadas
**Duración estimada:** 3-4 semanas  
**Objetivo:** Suite completa de herramientas de productividad integradas en el agente

**Referencia del documento:** §21-§77 (selección de módulos de alto valor)

### Entregables

#### Productividad Core
- [x] **Clipboard Inteligente (§21):** historial multi-clipboard, búsqueda semántica de copia, sincronización entre dispositivos
- [ ] **Bandeja de Entrada Unificada (§22):** emails + mensajes de todos los canales en una sola vista con IA de priorización
- [ ] **File Manager Inteligente (§37):** organización automática por contenido, búsqueda semántica de archivos, detección de duplicados
- [x] **Notificaciones Inteligentes (§25):** priorización por urgencia + contexto, supresión durante tareas críticas, resumen periódico

#### Web y Datos
- [ ] **Scraping + Data Extraction (§34):** extracción estructurada de cualquier web, con anti-detección y navegación de paginación
- [ ] **API Tester Inteligente (§49):** tipo Postman con IA, generación automática de colecciones desde OpenAPI spec
- [x] **Price Tracker (§39):** monitoreo multi-tienda, alertas de bajada de precio, gráfico histórico
- [ ] **Monitor de Reputación Online (§64):** menciones de marca en redes, noticias y foros en tiempo real

#### Contenido y Creación
- [ ] **Generación y Edición de Imágenes IA (§61):** DALL-E, Stable Diffusion, upscaling, inpainting, batch processing
- [ ] **Batch Image Processor (§51):** redimensionar, convertir, comprimir, watermarking en lote
- [ ] **SEO Auditor y Auto-Blogger (§77):** auditoría técnica de SEO, generación de artículos optimizados, publicación automática
- [ ] **Mind Maps y Diagramas (§59):** generación automática desde texto o conversación, export a Mermaid/SVG/PNG

#### Sistema y PC
- [x] **System Optimizer (§46):** limpieza de temporales, desfragmentación, análisis de startup, monitoreo de recursos
- [ ] **Sync + Backup Manager (§52):** backup incremental configurable a cloud o disco externo, restauración selectiva
- [ ] **Proxy / VPN Manager (§24):** rotación de proxies, VPN por tarea, geolocalización configurable por sub-agente
- [ ] **OCR de Documentos Físicos (§55):** modo escáner con cámara, corrección de perspectiva, export a PDF/Word

#### Multimedia y Comunicación
- [ ] **Videollamadas y Streaming (§71):** integración con Zoom/Meet (join, mute, compartir pantalla), control OBS Studio
- [ ] **Llamadas Telefónicas Automatizadas (§62):** voz sintética para recordatorios, confirmaciones y seguimientos
- [ ] **Audio/Podcast Manager (§45):** transcripción, resumen, generación de notas de episodio, publicación a RSS

**✅ Entregable final:** Suite completa de más de 15 herramientas especializadas integradas en el agente, eliminando la necesidad de apps separadas para la mayoría de tareas de productividad.

---

## Fase 18 — Modo Offline + Sincronización + Pulido Final
**Duración estimada:** 3-4 semanas  
**Objetivo:** Producto final completo, resiliente offline, portable y listo para distribución

**Referencia del documento:** §29 Sync, §67 Multi-idioma, §68 Accesibilidad, §69 Auto-Update, §101 Offline Mode

### Entregables

#### Modo Offline Degradado (§101)
- [x] Detección automática de conectividad
- [x] Estado **Online:** operación normal cloud + local
- [x] Estado **Degradado:** prioriza modelos y herramientas locales (Ollama, Whisper, MeloTTS)
- [x] Estado **Offline estricto:** solo capacidades 100% locales
- [x] Transición transparente entre estados sin interrumpir tareas activas
- [x] Notificación al usuario del cambio de estado y capacidades disponibles

#### Sincronización entre Dispositivos (§29)
- [x] Sync de memoria, preferencias, skills y workflows entre instancias
- [x] Backend de sync: Supabase o self-hosted (configurable)
- [x] Resolución de conflictos por timestamp + merge inteligente
- [ ] Sincronización end-to-end encriptada
- [ ] Instalación en hasta 5 dispositivos por licencia

#### Deprecación de Skills y Workflows (§115)
- [x] Criterios: sin uso en 60d, tasa de éxito <50%, skill duplicada, API rota, costo/beneficio negativo
- [x] Ciclo de vida: Activa → En revisión (60d sin uso) → Archivada (7d sin respuesta)
- [x] Reporte semanal de salud del ecosistema cada lunes
- [x] Auto-archivado si skill rota ≥14 días

#### Protocolo de Handoff entre Agentes Externos (§125)
- [ ] Integración con Claude Agent (Anthropic), ChatGPT Agent (OpenAI), Gemini Agent (Google)
- [ ] Transferencia de contexto y tarea a agente externo con resumen estructurado
- [ ] Recepción de resultados y continuación del flujo local

#### Accesibilidad e Internacionalización (§67, §68)
- [ ] Soporte multi-idioma: detección automática del idioma del sistema
- [x] Todos los idiomas soportados por los modelos LLM integrados
- [ ] Modo alto contraste y accesibilidad (ARIA, screen readers)
- [ ] Shortcuts de teclado configurables

#### Auto-Update (§69)
- [x] Verificación de nuevas versiones en background
- [x] Descarga e instalación silenciosa con reinicio diferido
- [x] Canal de actualización: estable / beta (configurable)
- [x] Rollback a versión anterior si la nueva falla

#### Pulido y Distribución Final
- [ ] Temas UI: Dark / Light / System / Custom
- [x] Inicio automático con Windows (configurable)
- [ ] Empaquetado NSIS installer con firma de código (Code Signing)
- [ ] Alternativa: compilación Nuitka para antivirus
- [ ] Testing end-to-end de todos los módulos
- [ ] Documentación completa (§117 SOP Generator aplicado al propio agente)
- [ ] Onboarding interactivo para nuevos usuarios (§30)
- [ ] KPIs de éxito validados (§92)

**✅ Entregable final:** G-Mini Agent v1.0 — producto completo, firmado, portable, con operación offline, sincronización multi-dispositivo y listo para distribución como instalador Windows.

---

## Resumen de Capacidades por Fase Acumuladas

```
Fase 1  ████████████████████  Chat multi-LLM + UI                    ✅ Alta
Fase 2  ████████████████████  + Ver y controlar PC/Android           ✅ Alta  ← CORE DIFERENCIADOR
Fase 3  ██████████████████░░  + Personaje animado + Voz              ✅ Media-Alta
Fase 4  ████████████████████  + Modos + Sub-agentes + Critic         ✅ Alta
Fase 5  ██████████████░░░░░░  + Integraciones externas               ✅ Media
Fase 6  ████████████████████  + WhatsApp/Telegram/Discord/Slack      ✅ Alta
Fase 7  ██████████████████░░  + Dispositivos + Smart Home            ✅ Media-Alta
Fase 8  ██████████████████░░  + Canvas + Skills + Cron               ✅ Media-Alta
Fase 9  ████████████████████  + 24/7 + Presupuesto                   ✅ Alta
Fase 10 ████████████████████  + Seguridad + RBAC + Políticas         ✅ Completa
Fase 11 ████████████████████  + Memoria LTM + Knowledge Graph        ✅ Completa
Fase 12 ██████████████████░░  + RPA + Macros + Rollback              ✅ Completa
Fase 13 ████████████████████  + Analytics + DAG + Goal Engine        ✅ Completa
Fase 14 ████████████████████  + Event Bus + Self-Healing + Versiones ✅ Completa
Fase 15 ████████████████████  + ETL + Alertas + RLHF                ✅ Completa
Fase 16 ████████████████████  + Agentes Autónomos                    ✅ Completa
Fase 17 ██████████████░░░░░░  + Productividad Avanzada              ✅ Completa (core)
Fase 18 ██████████████████░░  + Offline + Sync + Auto-Update        ✅ Completa (core)
```

---

## Dependencias entre Fases

```
Fase 1
  └─→ Fase 2 (requiere backend activo)
        └─→ Fase 3 (requiere overlay Electron)
              └─→ Fase 4 (requiere sistema de modos + sub-agentes)
                    ├─→ Fase 5 (requiere extensión Chrome + APIs)
                    ├─→ Fase 6 (requiere Gateway + sesiones)
                    └─→ Fase 7 (requiere Nodes + WebSocket)
                          ├─→ Fase 8 (requiere Skills + Cron)
                          └─→ Fase 9 (requiere checkpoints + presupuesto)
                                ├─→ Fase 10 (requiere RBAC + políticas)
                                ├─→ Fase 11 (requiere memoria + KG)
                                └─→ Fase 12 (requiere grabación + rollback)
                                      ├─→ Fase 13 (requiere DAG + Goals)
                                      └─→ Fase 14 (requiere Event Bus)
                                            ├─→ Fase 15 (ETL, Alertas, RLHF)
                                            ├─→ Fase 16 (Agentes especializados)
                                            ├─→ Fase 17 (Features productividad)
                                            └─→ Fase 18 (Offline + Pulido Final)
```

---

## Criterios de Éxito (KPIs Objetivo — §92)

| Métrica | Objetivo | Fase |
|---------|----------|------|
| Tiempo de respuesta (texto) | < 3s | Fase 1 |
| Captura + OCR | < 1s | Fase 2 |
| Precisión de clicks en UI | > 90% | Fase 2 |
| Latencia TTS (GPU) | < 2s/frase | Fase 3 |
| Inicio de la app | < 10s | Fase 1 |
| Tasa de éxito en tareas simples | > 85% | Fase 2-4 |
| Conflictos entre agentes resueltos sin humano | > 90% | Fase 16 |
| Tiempo de resolución de conflicto | < 200ms | Fase 16 |
| Deadlocks detectados y resueltos | 100% | Fase 16 |
| Cobertura offline de capacidades | > 70% local | Fase 18 |
