# G-Mini Agent — Documento de Definición del Proyecto

**Versión:** 1.0  
**Fecha actualizacion:** 5 de marzo de 2026  
**Estado:** Aprobado para desarrollo

---

## Índice

1. [Visión General](#1-visión-general)
2. [Decisiones de Arquitectura Aprobadas](#2-decisiones-de-arquitectura-aprobadas)
3. [Sistema de Modos](#3-sistema-de-modos)
4. [Sistema de Sub-Agentes](#4-sistema-de-sub-agentes)
5. [Sistema de Terminales (Multi-Shell)](#5-sistema-de-terminales-multi-shell)
6. [Extensión de Chrome (Control de Navegador)](#6-extensión-de-chrome-control-de-navegador)
7. [Integraciones y APIs Externas](#7-integraciones-y-apis-externas)
8. [Gateway Multi-Canal](#8-gateway-multi-canal)
9. [Sistema de Nodes (Dispositivos Conectados)](#9-sistema-de-nodes-dispositivos-conectados)
10. [Canvas (Dashboards Interactivos)](#10-canvas-dashboards-interactivos)
11. [Sistema de Skills (Plugins)](#11-sistema-de-skills-plugins)
12. [Automatización Programada (Cron)](#12-automatización-programada-cron)
13. [Tareas 24/7 (Background Jobs)](#13-tareas-247-background-jobs)
14. [Sistema de Presupuesto y Recursos](#14-sistema-de-presupuesto-y-recursos)
15. [Restricciones Éticas y Legales](#15-restricciones-éticas-y-legales)
16. [Memoria a Largo Plazo (Memory System)](#16-memoria-a-largo-plazo-memory-system)
17. [Grabación de Pantalla + Replay](#17-grabación-de-pantalla--replay)
18. [Macros / Workflows Grabables (RPA)](#18-macros--workflows-grabables-rpa)
19. [Sistema de Rollback / Undo](#19-sistema-de-rollback--undo)
20. [Analytics del Agente (Dashboard de Rendimiento)](#20-analytics-del-agente-dashboard-de-rendimiento)
21. [Clipboard Inteligente (Multi-Clipboard)](#21-clipboard-inteligente-multi-clipboard)
22. [Bandeja de Entrada Unificada](#22-bandeja-de-entrada-unificada)
23. [Modo Test / Dry Run](#23-modo-test--dry-run)
24. [Proxy / VPN Manager](#24-proxy--vpn-manager)
25. [Notificaciones Inteligentes con Prioridad](#25-notificaciones-inteligentes-con-prioridad)
26. [Handoff Humano (Human-in-the-Loop)](#26-handoff-humano-human-in-the-loop)
27. [Vault de Credenciales](#27-vault-de-credenciales)
28. [A/B Testing Automático](#28-ab-testing-automático)
29. [Sincronización entre Dispositivos](#29-sincronización-entre-dispositivos)
30. [Sistema de Tutoriales / Onboarding](#30-sistema-de-tutoriales--onboarding)
31. [Red de PCs (Multi-PC Control)](#31-red-de-pcs-multi-pc-control)
32. [Hogar Inteligente (Smart Home / IoT)](#32-hogar-inteligente-smart-home--iot)
33. [Proveedores de IA Compatibles](#33-proveedores-de-ia-compatibles)
34. [Stack Tecnológico](#34-stack-tecnológico)
35. [Sistema de Visión](#35-sistema-de-visión)
36. [Sistema de Automatización](#36-sistema-de-automatización)
37. [Asistente Virtual (Personaje Flotante)](#37-asistente-virtual-personaje-flotante)
38. [Interfaz de Usuario (Electron)](#38-interfaz-de-usuario-electron)
39. [Estructura del Proyecto](#39-estructura-del-proyecto)
40. [Comunicación Electron ↔ Python](#40-comunicación-electron--python)
41. [Manejo de DPI y Multi-Monitor](#41-manejo-de-dpi-y-multi-monitor)
42. [Seguridad y Sandboxing](#42-seguridad-y-sandboxing)
43. [Fases de Desarrollo (MVP Incremental)](#43-fases-de-desarrollo-mvp-incremental)
44. [Dependencias Principales (Python)](#44-dependencias-principales-python)
45. [Dependencias Frontend (Electron)](#45-dependencias-frontend-electron)
46. [Riesgos y Mitigaciones](#46-riesgos-y-mitigaciones)
47. [KPIs de Éxito](#47-kpis-de-éxito)
48. [Glosario](#48-glosario)

---

## 1. Visión General

**G-Mini Agent** es un **super-agente de IA autónomo** (.exe para Windows) capaz de controlar **gráficamente TODA la PC** y ejecutar tareas complejas de principio a fin como lo haría un humano experto.

### 1.1 Filosofía Central

> **"Si un humano puede hacerlo en una computadora, G-Mini Agent debe poder hacerlo."**

No es un asistente que solo responde preguntas. Es un **agente operativo** que:
- Ejecuta tareas completas de múltiples pasos
- Toma decisiones autónomas cuando encuentra obstáculos
- Busca alternativas si algo no funciona
- Opera 24/7 en background sin supervisión constante
- Genera valor real (dinero, productividad, resultados tangibles)

### 1.2 Capacidades Core

| Capacidad | Descripción |
|-----------|-------------|
| **Ver** | Captura de pantalla, OCR, comprensión de UI (OmniParser), reconocimiento de patrones visuales |
| **Pensar** | Razonamiento con cualquier LLM (cloud o local), planificación multi-paso, toma de decisiones |
| **Actuar** | Control total del escritorio (clicks, teclado, navegación), control de Android (ADB/scrcpy) |
| **Hablar** | Síntesis de voz (MeloTTS), conversación real-time, STT para escuchar |
| **Integrar** | APIs externas, redes sociales, editores, navegadores multi-perfil, herramientas de automatización |
| **Persistir** | Tareas 24/7 en background, checkpoints, recuperación de errores |
| **Delegar** | Crear sub-agentes especializados para tareas paralelas |
| **Adaptarse** | Cambiar de estrategia si algo falla, buscar alternativas, aprender de errores |

### 1.3 Diferenciador Clave

**Lo que NO es G-Mini Agent:**
```
❌ "Busca artículos sobre X y agrúpalos" → Solo recopila info, no genera valor
❌ "Notifica cuando encuentres Y" → Solo monitorea, no actúa
❌ "Crea un resumen de Z" → Solo procesa, no ejecuta el flujo completo
```

**Lo que SÍ es G-Mini Agent:**
```
✅ "Busca artículos sobre espionaje digital, crea carruseles para TikTok/X/FB/IG, 
    edita un video viral estilo Lord Draugr con clips de IA, música sin copyright,
    genera descripción y hashtags, y súbelo. Envíame preview a WhatsApp para aprobar."
    
✅ "Tengo 19 perfiles de Chrome con páginas de Facebook unidas a 100 grupos.
    Configura FewFeed2 en cada perfil, programa publicaciones para mi negocio,
    automatiza el proceso, verifica que funcione, y luego replica todo en un VPS Windows."
    
✅ "Juega Clash Royale y súbeme a 10k copas. Si mi PC no corre emulador, conecta
    mi celular por scrcpy. Si necesitas entrenar un modelo, hazlo en Colab."
```

### 1.4 Principio de Autonomía Restringida

El agente **puede hacer casi todo**, pero opera bajo restricciones configurables:

| Nivel | Comportamiento |
|-------|---------------|
| **Libre** | Ejecuta todo sin pedir confirmación (máxima autonomía) |
| **Supervisado** | Pide confirmación para acciones críticas (pagos, publicaciones, eliminaciones) |
| **Asistido** | Solo sugiere acciones, el usuario las aprueba una por una |
| **Presupuestado** | Opera libremente hasta un límite de gasto/acciones definido |

---

## 2. Decisiones de Arquitectura Aprobadas

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| Runtime ML | Todo incluido (PyTorch + PaddlePaddle) | Experiencia completa sin descargas adicionales |
| SikuliX | No incluir | OmniParser + PyAutoGUI cubre 95% de casos |
| Framework UI | Electron + Python backend | Máxima flexibilidad visual, diseño web moderno |
| Estrategia | MVP incremental (5 fases) | Funcional rápido, iterar sobre base sólida |
| Sub-agentes | Sí, arquitectura multi-agente | Permite tareas paralelas y especializadas |
| Modos | Sistema de modos intercambiables | Personaliza comportamiento según contexto |
| Control remoto | WhatsApp/Telegram | Permite comandar al agente desde el celular |

---

## 3. Sistema de Modos

El agente opera bajo **modos** que definen su personalidad, enfoque, permisos y comportamiento. El usuario puede cambiar de modo en cualquier momento (desde la app o remotamente por WhatsApp/Telegram).

### 3.1 Modos Predefinidos

| Modo | Descripción | Comportamiento |
|------|-------------|----------------|
| **🔧 Programador** | Asistente de desarrollo | Escribe/revisa código, debuggea, ejecuta comandos de terminal, gestiona Git, despliega |
| **📈 Marketero** | Experto en marketing digital | Crea campañas ads, gestiona redes sociales, diseña creativos, analiza métricas |
| **💼 Asesor de Ventas** | Vendedor y closer | Responde leads, hace seguimiento, negocia, cierra ventas por chat/llamada |
| **🔍 Investigador** | OSINT y research | Investiga personas/empresas, busca información, crea reportes, usa APIs de búsqueda |
| **🛡️ Pentester** | Seguridad ofensiva | Audita apps **locales o con source code**, no sistemas externos sin permiso |
| **📚 Tutor/Coach** | Educador y motivador | Enseña, crea planes de estudio, hace seguimiento de progreso, motiva |
| **👨‍👩‍👧 Padre Digital** | Supervisor de productividad | Vigila metas, limita distracciones, notifica sobre compromisos, gestiona horarios |
| **🛡️ Hermano Protector** | Bienestar y seguridad | Monitorea tiempo de pantalla, recuerda gym/compromisos, pide ubicación si necesario |
| **🎮 Gamer** | Juega y automatiza juegos | Controla juegos por visión, entrena modelos si necesario, gana partidas |
| **🎬 Creador de Contenido** | Producción multimedia | Edita videos, crea thumbnails, genera clips con IA, sube contenido |
| **🤖 Normal** | Asistente general | Modo default, puede hacer de todo sin especialización |

### 3.2 Cambiar de Modo

**Desde la app:**
```
[Dropdown en la UI] → Seleccionar modo → Confirmar
```

**Desde WhatsApp/Telegram (control remoto):**
```
Usuario: "Cambia a modo marketero"
Agente: "✅ Modo cambiado a 📈 Marketero. ¿En qué campaña trabajamos?"

Usuario: "Crea campaña de FB Ads con 80 soles, ya tienes mi tarjeta"
Agente: [Ejecuta la tarea con permisos de modo marketero]
```

### 3.3 Modos Personalizados

El usuario puede crear modos custom con prompt de sistema específico:

```yaml
modo_custom:
  nombre: "Asistente de Contabilidad"
  icono: "📊"
  system_prompt: |
    Eres un experto en contabilidad peruana. Ayudas a organizar facturas,
    calcular impuestos, generar reportes para SUNAT, y automatizar procesos
    contables. Usas Excel, sistemas de facturación, y conoces las leyes
    tributarias de Perú.
  permisos:
    - acceso_archivos: true
    - acceso_excel: true
    - acceso_navegador: true
    - realizar_pagos: false  # Por seguridad
  restricciones:
    - no_modificar_facturas_emitidas
```

### 3.4 Modo Activo + Sub-agentes

El agente principal puede mantener su modo y **crear sub-agentes** con otros modos:

```
Usuario: [Modo Normal] "Haz una campaña de marketing y también revisa mi código"

Agente Principal (Normal):
  "Voy a crear dos sub-agentes para esto:"
  
  → Sub-agente 1 (📈 Marketero): Trabajando en campaña de FB Ads...
  → Sub-agente 2 (🔧 Programador): Revisando tu código en /proyecto...
  
  "Te notifico cuando ambos terminen."
```

---

## 4. Sistema de Sub-Agentes

G-Mini Agent puede crear **sub-agentes especializados** que trabajan en paralelo, cada uno con su propio modo, contexto y tarea.

### 4.1 Arquitectura Multi-Agente

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENTE PRINCIPAL                          │
│                    (Orquestador)                            │
│                                                              │
│  - Recibe tareas del usuario                                │
│  - Decide si ejecutar directamente o delegar               │
│  - Crea y supervisa sub-agentes                            │
│  - Consolida resultados                                     │
│  - Reporta al usuario                                       │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Sub-Agent│ │Sub-Agent│ │Sub-Agent│
   │📈 Mkt   │ │🔧 Dev   │ │🎬 Video │
   │         │ │         │ │         │
   │Campaña  │ │Fix bug  │ │Editar   │
   │FB Ads   │ │API      │ │video    │
   └─────────┘ └─────────┘ └─────────┘
```

### 4.2 Cuándo se Crean Sub-Agentes

| Escenario | Comportamiento |
|-----------|----------------|
| Tarea única simple | Agente principal la ejecuta directamente |
| Tarea compleja con múltiples dominios | Crea sub-agentes especializados |
| Tareas que pueden paralelizarse | Sub-agentes trabajan simultáneamente |
| Tarea larga 24/7 | Sub-agente dedicado en background |
| Usuario pide explícitamente | "Crea un sub-agente para X" |

### 4.3 Comunicación entre Agentes

```
Agente Principal                    Sub-Agente (Marketero)
      │                                    │
      │─── Crear tarea: "Campaña FB" ───→ │
      │                                    │
      │                              [Ejecutando...]
      │                                    │
      │←── Progreso: 30% completado ───── │
      │                                    │
      │                              [Ejecutando...]
      │                                    │
      │←── Completado + resultados ─────── │
      │                                    │
      │─── Aprobar / Modificar ──────────→ │
      │                                    │
      ▼                                    ▼
[Reporta al usuario]              [Finaliza o continúa]
```

### 4.4 Límites de Sub-Agentes

| Recurso | Límite Default | Configurable |
|---------|----------------|--------------|
| Sub-agentes simultáneos | 5 | Sí |
| Tokens por sub-agente | Compartido del principal | Sí |
| Tiempo máximo de vida | 24 horas | Sí |
| Acceso a recursos | Heredado del principal | Sí (con restricciones) |

---

## 5. Sistema de Terminales (Multi-Shell)

El modo Programador (y sub-agentes programadores) tiene acceso completo a **todas las terminales** disponibles en el sistema.

### 5.1 Terminales Soportadas

| Terminal | Detección | Uso Principal |
|----------|-----------|---------------|
| **PowerShell** | `where powershell` | Scripts Windows, administración del sistema |
| **CMD** | Siempre disponible | Comandos legacy Windows |
| **Git Bash** | `where bash` (Git) | Git, scripts Unix-like en Windows |
| **WSL (Ubuntu/Debian/etc)** | `wsl --list` | Desarrollo Linux, Docker, Node, Python |
| **Windows Terminal** | Wrapper de otras terminales | Integración unificada |
| **Cmder/ConEmu** | Detección de instalación | Terminales avanzadas |
| **Bash/Zsh** (Linux/macOS) | `/bin/bash`, `/bin/zsh` | Desarrollo nativo |

### 5.2 Detección Automática de Terminales

Al iniciar, el agente detecta todas las terminales disponibles:

```python
# Ejemplo de detección
terminales_disponibles = {
    "powershell": {
        "path": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "disponible": True,
        "version": "5.1.19041.1"
    },
    "pwsh": {
        "path": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        "disponible": True,
        "version": "7.4.0"
    },
    "gitbash": {
        "path": "C:\\Program Files\\Git\\bin\\bash.exe",
        "disponible": True,
        "version": "5.2.21"
    },
    "wsl_ubuntu": {
        "path": "wsl -d Ubuntu",
        "disponible": True,
        "distro": "Ubuntu-22.04"
    },
    "wsl_debian": {
        "path": "wsl -d Debian",
        "disponible": True,
        "distro": "Debian"
    },
    "cmd": {
        "path": "C:\\Windows\\System32\\cmd.exe",
        "disponible": True
    }
}
```

### 5.3 Selección Inteligente de Terminal

El agente **decide automáticamente** qué terminal usar según la tarea:

| Tarea | Terminal Elegida | Razón |
|-------|------------------|-------|
| `npm install`, `node script.js` | WSL o Git Bash | Mejor compatibilidad Node.js |
| `pip install`, `python script.py` | WSL o PowerShell | Según entorno virtual |
| `git clone`, `git push` | Git Bash | Herramientas Git nativas |
| `docker build`, `docker-compose` | WSL | Docker Desktop integrado |
| `choco install`, `winget` | PowerShell (Admin) | Gestores de paquetes Windows |
| `apt install`, `sudo` | WSL | Comandos Linux |
| Scripts `.ps1` | PowerShell | Scripts nativos |
| Scripts `.sh` | Git Bash o WSL | Scripts Unix |
| `kubectl`, `terraform` | WSL o PowerShell | DevOps tools |

**Lógica de decisión:**
```
Tarea: "Instala dependencias del proyecto Node.js"
     │
     ├── Detectar: ¿Hay package.json? ✓
     │
     ├── Preferencias del proyecto:
     │   └── Si hay .nvmrc → usar terminal que soporte nvm (WSL/Git Bash)
     │
     ├── Terminales disponibles:
     │   └── WSL Ubuntu ✓, Git Bash ✓, PowerShell ✓
     │
     ├── Decisión: WSL Ubuntu (mejor soporte npm/node)
     │
     └── Ejecutar: wsl -d Ubuntu -e bash -c "cd /mnt/c/proyecto && npm install"
```

### 5.4 Gestión de Múltiples Terminales Simultáneas

El agente puede tener **múltiples terminales activas** en paralelo:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TERMINAL MANAGER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Terminal 1: [WSL Ubuntu]           Estado: 🟢 Activa           │
│  └── Corriendo: npm run dev (watch mode)                        │
│  └── PID: 12345                                                 │
│                                                                  │
│  Terminal 2: [PowerShell]           Estado: 🟢 Activa           │
│  └── Corriendo: docker-compose up                               │
│  └── PID: 12346                                                 │
│                                                                  │
│  Terminal 3: [Git Bash]             Estado: 🔵 Idle             │
│  └── Última: git status (completado)                            │
│                                                                  │
│  Terminal 4: [WSL Ubuntu]           Estado: 🟡 Background       │
│  └── Corriendo: python train_model.py                           │
│  └── Progreso: Epoch 45/100                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.5 Configuración de Terminales

```yaml
terminales:
  # Terminal preferida por defecto
  default: "wsl_ubuntu"  # o "powershell", "gitbash", etc.
  
  # Preferencias por tipo de tarea
  preferencias:
    node_js: "wsl_ubuntu"
    python: "wsl_ubuntu"
    git: "gitbash"
    docker: "wsl_ubuntu"
    windows_admin: "powershell"
    scripts_bat: "cmd"
  
  # WSL específico
  wsl:
    distro_default: "Ubuntu"
    mount_path: "/mnt/c"
    usar_wslpath: true
  
  # Límites
  max_terminales_simultaneas: 10
  timeout_inactividad: "30m"
  
  # Permisos
  permitir_sudo: true  # En WSL
  permitir_admin: false  # PowerShell elevado (requiere confirmación)
```

### 5.6 Ejemplos de Uso

**Desarrollo full-stack:**
```
Usuario: "Levanta el proyecto: frontend en React, backend en Python, y la base de datos"

Agente:
  Terminal 1 (WSL): cd /mnt/c/proyecto/backend && source venv/bin/activate && python manage.py runserver
  Terminal 2 (WSL): cd /mnt/c/proyecto/frontend && npm run dev
  Terminal 3 (PowerShell): docker-compose up postgres redis
  
  "✅ Proyecto levantado:
   - Backend: http://localhost:8000
   - Frontend: http://localhost:3000
   - Postgres: localhost:5432
   - Redis: localhost:6379"
```

**Git workflow:**
```
Usuario: "Haz commit de los cambios, crea un PR y despliega a staging"

Agente:
  Terminal (Git Bash):
    1. git add -A
    2. git commit -m "feat: implement user authentication"
    3. git push origin feature/auth
    4. gh pr create --title "User Auth" --body "..." --base develop
  
  Terminal (WSL):
    5. ssh staging "cd /app && git pull && docker-compose up -d"
  
  "✅ PR #123 creado y desplegado a staging"
```

---

## 6. Extensión de Chrome (Control de Navegador)

G-Mini Agent controla el navegador Chrome a través de una **extensión dedicada** que se conecta al servidor local del agente.

### 6.1 Arquitectura de la Extensión

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHROME                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              G-Mini Chrome Extension                         ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │ Content      │  │ Background   │  │ Popup UI     │       ││
│  │  │ Script       │  │ Service      │  │              │       ││
│  │  │              │  │ Worker       │  │ Estado:🟢    │       ││
│  │  │ • DOM access │  │              │  │ Conectado    │       ││
│  │  │ • Forms      │  │ • WebSocket  │  │              │       ││
│  │  │ • Clicks     │  │ • API calls  │  │ [Desconectar]│       ││
│  │  │ • Scroll     │  │ • Tabs mgmt  │  │              │       ││
│  │  └──────────────┘  └──────┬───────┘  └──────────────┘       ││
│  │                           │                                  ││
│  └───────────────────────────┼──────────────────────────────────┘│
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │ WebSocket
                               ▼
              ┌────────────────────────────────────┐
              │       G-MINI AGENT (Backend)       │
              │                                    │
              │  Puerto: ws://localhost:8765       │
              │                                    │
              │  Comandos:                         │
              │  • navigate(url)                   │
              │  • click(selector)                 │
              │  • type(selector, text)            │
              │  • screenshot()                    │
              │  • get_dom()                       │
              │  • execute_script(js)              │
              └────────────────────────────────────┘
```

### 6.2 Ventajas de Este Enfoque

| Aspecto | Beneficio |
|---------|-----------|
| **Sesiones preservadas** | Usa tus cookies, logins, contraseñas existentes |
| **Perfiles múltiples** | Cada perfil de Chrome puede tener la extensión |
| **Sin configuración** | No necesitas logearte de nuevo en sitios |
| **Extensiones existentes** | Tus otras extensiones siguen funcionando |
| **Datos del usuario** | Historial, bookmarks, autofill disponibles |
| **Menos detección** | Parece navegación humana real |

### 6.3 Instalación de la Extensión

**Automática (recomendado):**
```
Usuario: "Abre Facebook y publica esto"

Agente: "Para controlar Chrome necesito instalar mi extensión.
        
        Opciones:
        1. [Instalar automáticamente] - Abro Chrome y cargo la extensión
        2. [Instalar manualmente] - Te doy el link de Chrome Web Store
        3. [Usar modo PyAutoGUI] - Control visual sin extensión (más lento)
        
        ¿Qué prefieres?"

Usuario: "Instalar automáticamente"

Agente:
  1. Abre: chrome://extensions
  2. Habilita "Modo desarrollador"
  3. Carga extensión desde: %APPDATA%/gmini/chrome-extension/
  4. "✅ Extensión instalada. Conexión establecida."
```

**Manual (Chrome Web Store):**
```
1. Ve a: chrome.google.com/webstore/detail/gmini-agent/xxxxx
2. Click "Añadir a Chrome"
3. Acepta permisos
4. La extensión se conecta automáticamente al agente local
```

### 6.4 Perfiles de Chrome

El agente puede controlar **múltiples perfiles** de Chrome simultáneamente:

```
┌─────────────────────────────────────────────────────────────────┐
│                 CHROME PROFILE MANAGER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Perfil: "Personal"           Extensión: ✅    Conectado: 🟢    │
│  └── Sesiones: Gmail, Facebook, Twitter                         │
│                                                                  │
│  Perfil: "Trabajo"            Extensión: ✅    Conectado: 🟢    │
│  └── Sesiones: Slack, Jira, GitHub                              │
│                                                                  │
│  Perfil: "Marketing 1"        Extensión: ✅    Conectado: 🟢    │
│  └── Sesiones: FB Ads, Instagram Business                       │
│                                                                  │
│  Perfil: "Marketing 2"        Extensión: ❌    Conectado: ⚪    │
│  └── [Instalar extensión]                                        │
│                                                                  │
│  [+ Detectar perfiles]  [Instalar extensión en todos]           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Comando para instalar en múltiples perfiles:**
```
Usuario: "Instala la extensión en mis 19 perfiles de Chrome"

Agente:
  1. Detecta perfiles en: %LOCALAPPDATA%\Google\Chrome\User Data\
  2. Para cada perfil:
     - Abre Chrome con: chrome.exe --profile-directory="Profile X"
     - Navega a chrome://extensions
     - Carga la extensión
  3. "✅ Extensión instalada en 19 perfiles. Todos conectados."
```

### 6.5 Comandos de la Extensión

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `navigate` | Ir a una URL | `navigate("https://facebook.com")` |
| `click` | Click en elemento | `click("#login-button")` |
| `type` | Escribir texto | `type("#search", "query")` |
| `screenshot` | Captura de página | `screenshot()` → imagen base64 |
| `get_dom` | Obtener HTML/estructura | `get_dom()` → DOM simplificado |
| `get_text` | Extraer texto visible | `get_text("#content")` |
| `scroll` | Hacer scroll | `scroll("down", 500)` |
| `wait` | Esperar elemento | `wait("#modal", timeout=5)` |
| `execute_js` | Ejecutar JavaScript | `execute_js("document.title")` |
| `get_cookies` | Obtener cookies | `get_cookies("facebook.com")` |
| `fill_form` | Llenar formulario | `fill_form({...})` |
| `select_option` | Seleccionar dropdown | `select_option("#country", "Peru")` |
| `upload_file` | Subir archivo | `upload_file("#input", "/path/file")` |
| `new_tab` | Abrir nueva pestaña | `new_tab("https://...")` |
| `close_tab` | Cerrar pestaña | `close_tab(tab_id)` |
| `switch_tab` | Cambiar a pestaña | `switch_tab(tab_id)` |
| `list_tabs` | Listar pestañas | `list_tabs()` |

### 6.6 Ejemplo de Flujo Completo

```
Usuario: "Publica este carrusel en Instagram (ya estoy logueado)"

Agente (usando extensión):
  
  1. extension.navigate("https://instagram.com")
  2. extension.wait("#react-root", timeout=10)
  3. extension.click("[aria-label='New post']")
  4. extension.wait("[aria-label='Select from computer']")
  5. extension.upload_file("input[type=file]", ["img1.jpg", "img2.jpg", "img3.jpg"])
  6. extension.wait("[aria-label='Next']")
  7. extension.click("[aria-label='Next']")  # A filtros
  8. extension.click("[aria-label='Next']")  # A caption
  9. extension.type("[aria-label='Write a caption']", "Mi caption #hashtag")
  10. extension.click("[aria-label='Share']")
  11. extension.wait("Post shared", timeout=30)
  
  "✅ Carrusel publicado en Instagram"
```

### 6.7 Configuración de la Extensión

```yaml
chrome_extension:
  # Servidor WebSocket
  server:
    host: "127.0.0.1"
    port: 8765
    ssl: false  # true para wss:// en producción
  
  # Detección de Chrome
  chrome:
    detectar_perfiles: true
    perfiles_path: "%LOCALAPPDATA%\\Google\\Chrome\\User Data"
    perfiles_activos: ["Default", "Profile 1", "Profile 2"]
  
  # Comportamiento
  comportamiento:
    confirmar_acciones_sensibles: true  # Pagos, eliminar, etc.
    screenshot_antes_de_accion: true    # Para debugging
    timeout_default: 10  # segundos
    retry_on_fail: 3
  
  # Permisos por perfil
  permisos:
    "Default":
      permitir_pagos: false
      sitios_bloqueados: []
    "Marketing 1":
      permitir_pagos: true
      limite_gasto: 100  # USD
      sitios_permitidos: ["facebook.com", "instagram.com"]
```

### 6.8 Fallback: Modo PyAutoGUI

Si la extensión no está instalada o falla, el agente puede usar **PyAutoGUI** como fallback:

| Aspecto | Extensión | PyAutoGUI |
|---------|-----------|-----------|
| Velocidad | Rápida (API directa) | Lenta (visual) |
| Precisión | 100% (selectores) | ~95% (OCR/coords) |
| Sesiones | Preservadas | Preservadas |
| Configuración | Requiere extensión | Sin configuración |
| Detección anti-bot | Muy baja | Baja |
| Multi-pestaña | Fácil | Complejo |

```
Decisión automática:
  Si extensión conectada → usar extensión
  Si no → 
    Si tarea simple → usar PyAutoGUI
    Si tarea compleja → preguntar al usuario si instalar extensión
```

---

## 7. Integraciones y APIs Externas

G-Mini Agent se conecta con herramientas y servicios externos para ejecutar tareas complejas.

### 7.1 Integraciones de Primera Clase (Built-in)

| Categoría | Herramientas | Uso |
|-----------|-------------|-----|
| **Navegadores** | Chrome (multi-perfil), Firefox, Edge | Automatización web, login a cuentas, extensiones |
| **Redes Sociales** | Facebook, Instagram, X/Twitter, TikTok, LinkedIn, YouTube | Publicar, programar, interactuar, analytics |
| **Mensajería** | WhatsApp Web, Telegram, Discord | Enviar mensajes, recibir comandos, notificaciones |
| **Video** | CapCut, Premiere Pro, DaVinci, ffmpeg | Edición automática, render, exportar |
| **Imágenes** | Photoshop, Canva, GIMP, Figma | Diseño, edición, creativos |
| **Documentos** | Word, Excel, Google Docs/Sheets | Crear reportes, procesar datos |
| **Desarrollo** | VS Code, Terminal, Git, Docker | Programar, deployar, gestionar repos |
| **IA Generativa** | FlowGemini, Veo, Runway, ElevenLabs | Generar clips, voces, imágenes |
| **Pagos** | PayPal, Stripe, FB Ads, Google Ads | Gestionar presupuesto, crear campañas |
| **Android** | ADB, scrcpy, BlueStacks, Emuladores | Control de celular, juegos |

### 7.2 APIs Externas Soportadas

```yaml
apis_configurables:
  # OSINT / Investigación
  - pipl_api          # Búsqueda de personas
  - hunter_io         # Búsqueda de emails
  - shodan            # Búsqueda de dispositivos
  - builtwith         # Tecnologías de websites
  
  # Redes Sociales
  - facebook_graph    # API de Facebook/Instagram
  - twitter_api       # API de X
  - tiktok_api        # TikTok for Business
  
  # Servicios de IA
  - elevenlabs        # Clonación de voz
  - runway_ml         # Generación de video
  - midjourney        # Generación de imágenes
  - veo_google        # Video AI de Google
  
  # Productividad
  - notion_api        # Gestión de tareas
  - slack_api         # Comunicación de equipo
  - google_calendar   # Calendario
  - trello_api        # Kanban
  
  # Automatización
  - zapier            # Conectar apps
  - make_integromat   # Flujos de trabajo
  - n8n_local         # Automatización local
```

### 7.3 Navegador Multi-Perfil

G-Mini Agent puede manejar múltiples perfiles de Chrome simultáneamente:

```
Usuario: "Tengo 19 perfiles de Chrome, cada uno con una página de Facebook
          en grupos diferentes. Configura FewFeed2 en cada uno."

Agente:
  1. Detecta perfiles de Chrome instalados
  2. Abre Chrome con: chrome.exe --profile-directory="Profile 1"
  3. Navega a la extensión FewFeed2
  4. Configura según las instrucciones del usuario
  5. Repite para los 19 perfiles
  6. Verifica funcionamiento
  7. Si hay VPS → replica configuración remotamente
```

---

## 8. Gateway Multi-Canal

G-Mini Agent opera como un **gateway de comunicación multi-canal**, permitiendo interactuar con el agente desde múltiples plataformas simultáneamente.

### 8.1 Canales Soportados

| Canal | Tipo | Uso Principal |
|-------|------|---------------|
| **WhatsApp** | Mensajería | Control remoto desde celular |
| **Telegram** | Bot | Comandos, confirmaciones, notificaciones |
| **Discord** | Bot | Grupos, automatización de comunidades |
| **Slack** | App/Bot | Equipos de trabajo, integraciones enterprise |
| **Signal** | Puente | Mensajería segura |
| **Google Chat** | Bot | Workspace de Google |
| **Microsoft Teams** | Bot | Ambiente corporativo |
| **Matrix/Element** | Puente | Federación descentralizada |
| **IRC** | Puente | Comunidades técnicas |
| **iMessage** | macOS node | Ecosistema Apple |
| **App Desktop** | Nativo | Interfaz principal |
| **Web Chat** | WebSocket | Acceso desde navegador |

### 8.2 Arquitectura del Gateway

```
┌─────────────────────────────────────────────────────────────────┐
│                         G-MINI GATEWAY                           │
│                    (Control Plane + Router)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   WhatsApp ──┐                              ┌── Sesión Main      │
│   Telegram ──┤                              │                    │
│   Discord ───┤     ┌────────────────┐      ├── Sesión Trabajo   │
│   Slack ─────┼────→│ Session Router │─────→│                    │
│   Signal ────┤     └────────────────┘      ├── Sesión Proyecto1 │
│   WebChat ───┤                              │                    │
│   Desktop ───┘                              └── Sesión GrupoX    │
│                                                                  │
│   Eventos: agent | chat | presence | health | heartbeat | cron  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Sesiones y Contextos Separados

Cada conversación tiene su propia sesión con contexto aislado:

| Tipo de Chat | Sesión | Comportamiento |
|--------------|--------|----------------|
| Chat directo (1:1) | `main` | Contexto personal principal |
| Grupo con nombre | `group:{nombre}` | Contexto aislado del grupo |
| Canal de Slack/Discord | `channel:{id}` | Contexto del canal |
| Proyecto específico | `project:{nombre}` | Sesión dedicada al proyecto |

**Beneficio:** Lo de trabajo nunca se mezcla con lo personal.

```yaml
sesiones:
  main:
    tipo: "personal"
    contexto: "usuario principal"
    historial_max: 100
  
  grupo_trabajo:
    tipo: "grupo"
    contexto: "equipo de desarrollo"
    miembros_autorizados: ["@juan", "@maria"]
  
  proyecto_tiktok:
    tipo: "proyecto"
    contexto: "automatización de contenido TikTok"
    herramientas_permitidas: ["browser", "ffmpeg", "canvas"]
```

### 8.4 Activación por Mención (Grupos)

En grupos, el agente **solo responde cuando lo mencionan**:

```
Grupo de Discord:
  
  Juan: "¿Alguien tiene el reporte de ventas?"
  María: "Lo tengo en algún lado..."
  
  → (El agente NO responde, no lo mencionaron)
  
  Pedro: "@G-Mini haz un resumen de este hilo"
  
  → G-Mini: "📝 Resumen: Juan busca el reporte de ventas. 
             María dice tenerlo. ¿Quieres que lo busque en 
             los archivos compartidos?"
```

**Configuración:**
```yaml
grupos:
  activacion: "mention"  # solo cuando me mencionan
  prefijos_alternativos: ["gmini", "agente", "bot"]
  responder_siempre_a: ["@admin"]  # excepciones
```

### 8.5 Manejo de Adjuntos

El agente puede recibir y procesar archivos en cualquier canal:

| Tipo | Capacidad | Ejemplo |
|------|-----------|---------|
| **Imágenes** | OCR, análisis visual, edición | "¿Qué dice este screenshot?" |
| **PDFs** | Extracción, resumen, búsqueda | "Resume este contrato en 5 puntos" |
| **Audio** | Transcripción, análisis | "Transcribe esta nota de voz" |
| **Video** | Extracción de frames, transcripción | "¿De qué trata este video?" |
| **Documentos** | Word, Excel, análisis | "Extrae los datos de esta tabla" |
| **Código** | Análisis, ejecución, review | "Revisa este archivo Python" |

### 8.6 Acciones en Canales

El agente puede **ejecutar acciones** directamente en los canales:

| Acción | Canal | Ejemplo |
|--------|-------|---------|
| Postear mensaje | Slack/Discord | "Publica el resumen en #standup" |
| Crear hilo | Slack/Discord | "Crea hilo de discusión sobre X" |
| Mencionar usuarios | Cualquiera | "Etiqueta a @equipo cuando termines" |
| Reaccionar | Discord/Slack | "Pon ✅ cuando esté listo" |
| Fijar mensaje | Discord/Slack | "Pinea las instrucciones" |
| Crear canal | Discord/Slack | "Crea canal #proyecto-nuevo" |

### 8.7 Configuración del Gateway

```yaml
gateway:
  # Canales habilitados
  canales:
    whatsapp:
      enabled: true
      session_path: "./sessions/whatsapp"
      numeros_autorizados: ["+51XXXXXXXXX"]
    
    telegram:
      enabled: true
      bot_token: "${TELEGRAM_BOT_TOKEN}"
      chat_ids_autorizados: [123456789]
    
    discord:
      enabled: true
      bot_token: "${DISCORD_BOT_TOKEN}"
      guilds_autorizados: ["guild_id_1"]
      sandbox_en_grupos: true  # Más restrictivo en grupos
    
    slack:
      enabled: false
      app_token: "${SLACK_APP_TOKEN}"
  
  # Comportamiento
  sesiones:
    timeout_inactividad: "24h"
    max_historial: 100
    separar_contextos: true
  
  # Seguridad
  seguridad:
    solo_usuarios_autorizados: true
    sandbox_en_grupos: true
    tools_bloqueadas_grupos: ["exec", "browser", "nodes"]
```

---

## 9. Sistema de Nodes (Dispositivos Conectados)

G-Mini Agent puede **convertir dispositivos** (teléfonos, PCs, Raspberry Pi) en **nodos remotos** que actúan como sensores y actuadores.

### 9.1 Concepto de Nodes

Un **Node** es un dispositivo que se conecta al agente por WebSocket y expone **superficies de capacidades**:

```
┌─────────────────────────────────────────────────────────────────┐
│                       G-MINI AGENT (Host)                        │
│                                                                  │
│   Puede invocar: node.invoke(device, surface, action, params)   │
│                                                                  │
└───────────────────┬────────────────────┬────────────────────────┘
                    │                    │
           ┌────────┴────────┐  ┌────────┴────────┐
           │  📱 iOS Node    │  │  🤖 Android Node │
           │                 │  │                  │
           │ camera.*        │  │ camera.*         │
           │ location.*      │  │ location.*       │
           │ notifications.* │  │ notifications.*  │
           │ voice.*         │  │ device.*         │
           │ clipboard.*     │  │ contacts.*       │
           └─────────────────┘  │ sms.*            │
                                │ apps.*           │
           ┌─────────────────┐  └──────────────────┘
           │  💻 PC Node     │
           │  (Windows/Mac)  │  ┌─────────────────┐
           │                 │  │  🍓 Raspberry Pi │
           │ system.*        │  │                  │
           │ screen.*        │  │ gpio.*           │
           │ files.*         │  │ sensors.*        │
           │ exec.*          │  │ camera.*         │
           │ clipboard.*     │  └──────────────────┘
           └─────────────────┘
```

### 9.2 Superficies Disponibles por Plataforma

#### iOS Node

| Superficie | Acciones | Ejemplo |
|------------|----------|---------|
| `camera.*` | `take_photo`, `record_video`, `scan_qr` | "Toma foto del recibo" |
| `location.*` | `get_current`, `start_tracking` | "¿Dónde estacioné?" |
| `notifications.*` | `send`, `list_pending` | "Notifícame cuando llegue X" |
| `voice.*` | `speak`, `listen`, `transcribe` | "Dime esto en voz alta" |
| `clipboard.*` | `get`, `set` | "Copia esto al portapapeles" |
| `screen.*` | `capture`, `record` | "Graba mi pantalla 30 segundos" |
| `health.*` | `get_steps`, `get_heart_rate` | "¿Cuántos pasos hoy?" |

#### Android Node

| Superficie | Acciones | Ejemplo |
|------------|----------|---------|
| `camera.*` | `take_photo`, `record`, `scan` | "Escanea este documento" |
| `location.*` | `get_current`, `track` | "Guarda mi ubicación actual" |
| `notifications.*` | `send`, `read`, `dismiss` | "Lee mis notificaciones" |
| `device.*` | `vibrate`, `brightness`, `volume` | "Sube el volumen" |
| `contacts.*` | `search`, `get`, `create` | "Busca el contacto Pedro" |
| `sms.*` | `send`, `read`, `list` | "Manda SMS a Pedro con mi ETA" |
| `apps.*` | `open`, `list`, `install_status` | "Abre la app de banco" |
| `files.*` | `list`, `read`, `share` | "Comparte esta foto" |

#### PC/Mac Node (Host Remoto)

| Superficie | Acciones | Ejemplo |
|------------|----------|---------|
| `system.*` | `run`, `which`, `env`, `info` | "Corre el backup en mi PC de casa" |
| `screen.*` | `capture`, `record` | "Screenshot de mi otro monitor" |
| `files.*` | `read`, `write`, `list`, `watch` | "¿Qué hay en ~/Downloads?" |
| `clipboard.*` | `get`, `set` | "Pega esto allá" |
| `exec.*` | `command`, `script` | "Ejecuta el script de deploy" |

### 9.3 Ejemplos de Uso con Nodes

**Tomar foto y procesar:**
```
Usuario: "Toma una foto con mi móvil y extrae el texto"

Agente:
  1. node.invoke("iphone", "camera.take_photo", {})
  2. Recibe imagen
  3. OCR → extrae texto
  4. "El recibo dice: Total S/45.50, Fecha: 05/03/2026..."
```

**Notificación push condicional:**
```
Usuario: "Notifícame cuando llegue un correo de 'pago aprobado'"

Agente:
  1. Configura monitor de email
  2. Cuando detecta el correo:
     node.invoke("android", "notifications.send", {
       title: "💰 Pago Aprobado",
       body: "Recibiste confirmación de pago de $500",
       priority: "high"
     })
```

**Ejecutar en PC remota:**
```
Usuario: "En mi PC de casa, corre el script de backup"

Agente:
  1. Verifica que el node "pc-casa" está conectado
  2. Verifica permisos en exec-approvals.json
  3. node.invoke("pc-casa", "system.run", {
       command: "python /home/user/scripts/backup.py"
     })
  4. "✅ Backup completado. 15 GB sincronizados."
```

### 9.4 Configuración de Nodes

```yaml
nodes:
  # Dispositivos emparejados
  dispositivos:
    iphone_personal:
      tipo: "ios"
      nombre: "iPhone de Juan"
      session_key: "${IPHONE_SESSION_KEY}"
      superficies_permitidas: ["camera", "location", "notifications"]
    
    android_trabajo:
      tipo: "android"
      nombre: "Pixel de Trabajo"
      superficies_permitidas: ["camera", "notifications", "sms"]
      superficies_bloqueadas: ["contacts"]  # Por privacidad
    
    pc_casa:
      tipo: "host"
      nombre: "PC de Casa"
      superficies_permitidas: ["system", "files", "screen"]
      exec_approvals: "./config/exec-approvals-pc-casa.json"
  
  # Seguridad
  emparejamiento:
    requiere_confirmacion: true
    timeout_sesion: "7d"
    notificar_nuevas_conexiones: true
```

### 9.5 Seguridad de Nodes

| Aspecto | Medida |
|---------|--------|
| Emparejamiento | Requiere confirmación manual inicial |
| Session keys | Rotación automática cada 7 días |
| Exec approvals | Lista blanca de comandos permitidos por host |
| Logging | Todas las invocaciones se loguean |
| Sandbox | Nodes en grupos usan sandbox por defecto |

---

## 10. Canvas (Dashboards Interactivos)

G-Mini Agent puede generar y mantener **dashboards visuales en vivo** que se actualizan automáticamente.

### 10.1 Concepto de Canvas

Un **Canvas** es una superficie visual interactiva que:
- Muestra información en tiempo real
- Se actualiza automáticamente cuando cambian los datos
- Puede ser renderizada en la app, web, o en un node

```
┌─────────────────────────────────────────────────────────────┐
│                     CANVAS: "Tareas de Hoy"                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📋 To-Do                          📊 Progreso              │
│  ─────────────                     ───────────              │
│  [✅] Revisar emails (9:00)        ████████░░ 80%           │
│  [✅] Llamada con cliente                                    │
│  [🔄] Editar video TikTok          Completadas: 8/10        │
│  [ ] Publicar en redes             Pendientes: 2            │
│  [ ] Revisar analytics                                       │
│                                                              │
│  🕐 Próximo: "Publicar en redes" en 45 min                  │
│                                                              │
│  [Actualizado hace 2 min] [🔄 Refrescar] [⚙️ Config]        │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Tipos de Canvas

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| **Estado** | Mostrar estado actual del agente | Tareas activas, sub-agentes, recursos |
| **Dashboard** | Métricas y KPIs en vivo | Ventas, analytics, métricas de campaña |
| **Monitor** | Vigilar eventos/cambios | Emails nuevos, menciones, precios |
| **Workflow** | Visualizar flujos de trabajo | Pipeline de contenido, etapas de proyecto |
| **Lista** | To-dos, checklist, inventario | Tareas diarias, compras, pendientes |

### 10.3 Crear y Actualizar Canvas

**Crear canvas:**
```
Usuario: "Muéstrame un panel con mis tareas de hoy"

Agente:
  1. canvas.create({
       id: "tareas_hoy",
       tipo: "lista",
       titulo: "Tareas de Hoy",
       fuente: "google_calendar + notion",
       refresh_interval: "5m"
     })
  2. "📋 Canvas 'Tareas de Hoy' creado. Lo actualizo cada 5 minutos."
```

**Actualización automática:**
```
[Evento: tarea completada en Notion]
     │
     ▼
[Agente detecta cambio]
     │
     ▼
[canvas.update("tareas_hoy", { completadas: +1 })]
     │
     ▼
[Canvas se actualiza en tiempo real]
```

### 10.4 Canvas en Nodes

Los canvas pueden renderizarse en dispositivos conectados:

```
Usuario: "Muestra el dashboard de ventas en mi iPad"

Agente:
  1. Crea/obtiene canvas "dashboard_ventas"
  2. node.invoke("ipad", "canvas.render", {
       canvas_id: "dashboard_ventas",
       modo: "fullscreen"
     })
  3. El iPad muestra el dashboard en vivo
```

### 10.5 Ejemplos de Canvas

**Monitor de competencia:**
```yaml
canvas:
  id: "monitor_competencia"
  titulo: "Precios Competencia"
  tipo: "monitor"
  
  fuentes:
    - web_scrape: "competidor1.com/pricing"
    - web_scrape: "competidor2.com/plans"
    - api: "price_tracker_api"
  
  refresh: "1h"
  
  alertas:
    - condicion: "precio_competidor < mi_precio"
      accion: "notificar_urgente"
  
  visualizacion:
    tipo: "tabla_comparativa"
    columnas: ["Producto", "Mi Precio", "Comp1", "Comp2", "Diferencia"]
```

**Dashboard de contenido:**
```yaml
canvas:
  id: "content_dashboard"
  titulo: "🎬 Pipeline de Contenido"
  
  paneles:
    - titulo: "En Producción"
      tipo: "kanban"
      columnas: ["Ideas", "Grabando", "Editando", "Listo", "Publicado"]
    
    - titulo: "Métricas Últimos 7 Días"
      tipo: "chart"
      datos: ["views", "likes", "comments", "shares"]
    
    - titulo: "Próximas Publicaciones"
      tipo: "calendario"
      fuente: "scheduled_posts"
```

---

## 11. Sistema de Skills (Plugins)

G-Mini Agent soporta **skills instalables** que extienden sus capacidades sin modificar el core.

### 11.1 Concepto de Skills

Una **Skill** es un paquete que añade:
- Nuevas herramientas (tools)
- Nuevas integraciones (APIs)
- Nuevos comandos
- Nuevo conocimiento especializado

```
┌─────────────────────────────────────────────────────────────────┐
│                        SKILL REGISTRY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📦 Skills Instaladas (12)                                      │
│  ──────────────────────────                                      │
│  ✅ notion-integration    │ Crear páginas, bases de datos      │
│  ✅ ffmpeg-toolkit        │ Edición de video avanzada          │
│  ✅ social-media-suite    │ Publicar en FB/IG/X/TikTok        │
│  ✅ email-assistant       │ Gestión de Gmail/Outlook          │
│  ✅ finance-tracker       │ Contabilidad y facturas            │
│  ⏸️ shopify-connector     │ (Desactivada)                      │
│                                                                  │
│  📥 Skills Disponibles (Hub)                                    │
│  ─────────────────────────────                                   │
│  [🔍 Buscar skills...]                                          │
│                                                                  │
│  📂 Categorías: Dev Tools | Productividad | Marketing |         │
│                 Finanzas | Media | Comunicación | Datos         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Instalar Skills

**Desde comando:**
```
Usuario: "Instala una skill de Notion"

Agente:
  1. skill.search("notion")
  2. "Encontré 3 skills de Notion:
      1. notion-integration (oficial) ⭐4.8
      2. notion-database-sync ⭐4.5
      3. notion-to-markdown ⭐4.2
      
      ¿Cuál instalo?"
  
Usuario: "La primera"

Agente:
  1. skill.install("notion-integration")
  2. skill.configure("notion-integration", {api_key: "..."})
  3. "✅ Skill 'notion-integration' instalada. 
      Ahora puedo crear páginas, bases de datos, y más."
```

**Desde UI:**
```
Settings → Skills → Hub → Buscar → Instalar → Configurar
```

### 11.3 Estructura de una Skill

```yaml
# skill.yaml
name: "notion-integration"
version: "1.2.0"
description: "Integración completa con Notion"
author: "gmini-community"
category: "productividad"

# Requisitos
requires:
  api_keys: ["NOTION_API_KEY"]
  permissions: ["web_fetch", "files.read"]

# Tools que añade
tools:
  - name: "notion_create_page"
    description: "Crear una página en Notion"
    parameters:
      - name: "database_id"
        type: "string"
      - name: "title"
        type: "string"
      - name: "content"
        type: "markdown"
  
  - name: "notion_query_database"
    description: "Buscar en una base de datos de Notion"
    parameters:
      - name: "database_id"
        type: "string"
      - name: "filter"
        type: "object"

# Modo preferido (opcional)
suggested_mode: "programador"

# Comandos naturales
commands:
  - pattern: "crea página en notion"
    action: "notion_create_page"
  - pattern: "busca en notion"
    action: "notion_query_database"
```

### 11.4 Prioridad de Skills

```
Workspace skills (./skills/)     ← Mayor prioridad
        ↓
Local skills (~/.gmini/skills/)
        ↓
Bundled skills (instaladas)
        ↓
Remote registry (Hub)            ← Menor prioridad
```

### 11.5 Categorías de Skills Disponibles

| Categoría | Ejemplos |
|-----------|----------|
| **Dev Tools** | GitHub, GitLab, Jira, Linear, Docker, CI/CD |
| **Productividad** | Notion, Todoist, Trello, Asana, Calendar |
| **Marketing** | HubSpot, Mailchimp, Facebook Ads, Google Ads |
| **Finanzas** | QuickBooks, Stripe, PayPal, Facturación |
| **Media** | FFmpeg, ImageMagick, Canva, Adobe APIs |
| **Comunicación** | Email, Calendly, Zoom, Meet |
| **Datos** | Airtable, Google Sheets, SQL connectors |
| **E-commerce** | Shopify, WooCommerce, Amazon Seller |
| **OSINT** | Hunter.io, Shodan, BuiltWith, WHOIS |

### 11.6 Crear Skills Personalizadas

Los usuarios pueden crear sus propias skills:

```
skills/
└── mi-skill/
    ├── skill.yaml      # Metadata y configuración
    ├── tools/
    │   ├── mi_tool_1.py
    │   └── mi_tool_2.py
    └── README.md
```

---

## 12. Automatización Programada (Cron)

G-Mini Agent puede ejecutar tareas automáticamente según horarios definidos.

### 12.1 Sistema de Cron

```
┌─────────────────────────────────────────────────────────────┐
│                   CRON SCHEDULER                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ID        Expresión       Próxima        Tarea             │
│  ─────────────────────────────────────────────────────────  │
│  cron_1   0 8 * * *       Hoy 08:00      Revisar emails     │
│  cron_2   0 9 * * 1       Lun 09:00      Reporte semanal    │
│  cron_3   */6 * * *       Hoy 18:00      Check leads        │
│  cron_4   0 20 * * *      Hoy 20:00      Backup diario      │
│  cron_5   0 0 1 * *       01/Abr 00:00   Facturación        │
│                                                              │
│  [+ Nueva tarea programada]                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 Crear Tareas Programadas

**Lenguaje natural:**
```
Usuario: "Todos los días a las 8am, revisa mis emails y avísame si hay algo urgente"

Agente:
  1. cron.create({
       expresion: "0 8 * * *",
       tarea: "Revisar emails y notificar urgentes",
       acciones: [
         "email.check_inbox",
         "email.filter(priority: high)",
         "notifications.send_if_found"
       ]
     })
  2. "✅ Tarea programada. Cada día a las 8:00 AM revisaré tus emails."
```

**Configuración YAML:**
```yaml
cron_jobs:
  - id: "morning_emails"
    expresion: "0 8 * * *"  # Cada día 8am
    tarea: "Revisar emails urgentes"
    acciones:
      - herramienta: "email.check_inbox"
        parametros: { account: "trabajo" }
      - herramienta: "email.filter"
        parametros: { priority: "high", unread: true }
      - condicion: "resultados > 0"
        entonces:
          - herramienta: "notifications.send"
            parametros: 
              canal: "whatsapp"
              mensaje: "📧 Tienes {count} emails urgentes"
  
  - id: "weekly_report"
    expresion: "0 9 * * 1"  # Lunes 9am
    tarea: "Generar y enviar reporte semanal"
    modo: "marketero"
    acciones:
      - herramienta: "analytics.get_weekly"
      - herramienta: "document.create_report"
      - herramienta: "slack.post"
        parametros: { channel: "#reports" }
  
  - id: "price_monitor"
    expresion: "0 */4 * * *"  # Cada 4 horas
    tarea: "Monitorear precios de competencia"
    acciones:
      - herramienta: "web_scrape"
        parametros: { urls: ["competidor1.com", "competidor2.com"] }
      - herramienta: "canvas.update"
        parametros: { canvas_id: "precios_competencia" }
```

### 12.3 Tipos de Triggers

| Tipo | Expresión | Ejemplo |
|------|-----------|---------|
| **Cron clásico** | `0 8 * * *` | Cada día a las 8am |
| **Intervalo** | `@every 30m` | Cada 30 minutos |
| **Heartbeat** | `@heartbeat` | Cada ciclo del sistema |
| **Evento** | `@on email.new` | Cuando llega un email |
| **Webhook** | `@webhook /trigger/x` | Cuando se llama al endpoint |

### 12.4 Condiciones y Lógica

```yaml
cron_job:
  id: "smart_reminder"
  expresion: "0 * * * *"  # Cada hora
  
  condiciones:
    - tipo: "hora"
      entre: ["09:00", "18:00"]  # Solo horario laboral
    
    - tipo: "dia"
      no_incluye: ["sabado", "domingo"]  # No fines de semana
    
    - tipo: "estado"
      agente: "idle"  # Solo si no está ocupado
  
  acciones:
    - herramienta: "calendar.check_upcoming"
      si_resultado:
        tiene_eventos:
          - herramienta: "notifications.send"
            mensaje: "🗓️ En 15 min: {evento}"
```

### 12.5 Gestión de Cron

| Comando | Ejemplo | Acción |
|---------|---------|--------|
| Listar | "¿Qué tareas programadas tengo?" | Muestra todas |
| Crear | "Cada viernes envía reporte" | Crea nueva |
| Pausar | "Pausa la tarea de emails" | Desactiva temporalmente |
| Eliminar | "Cancela el monitor de precios" | Elimina |
| Historial | "¿Cuándo corrió el backup?" | Muestra ejecuciones |

---

## 13. Tareas 24/7 (Background Jobs)

G-Mini Agent puede ejecutar tareas de larga duración que persisten incluso si se reinicia la PC.

### 13.1 Tipos de Tareas

| Tipo | Duración | Ejemplo |
|------|----------|---------|
| **One-shot** | Minutos-horas | "Edita este video y súbelo" |
| **Recurrente** | Diario/semanal | "Cada lunes publica resumen semanal" |
| **Continua** | Indefinida | "Juega hasta llegar a 10k copas" |
| **Monitoreada** | Indefinida | "Vigila mi email y responde leads" |

### 13.2 Sistema de Checkpoints

Para tareas largas, el agente guarda progreso periódicamente:

```yaml
checkpoint:
  task_id: "video_edit_123"
  created_at: "2026-03-05T10:00:00"
  last_update: "2026-03-05T14:30:00"
  status: "in_progress"
  progress: 65%
  current_step: "adding_narration"
  completed_steps:
    - download_video
    - cut_clips
    - add_music
  pending_steps:
    - adding_narration
    - final_render
    - upload
  state:
    video_path: "/tmp/edit/video.mp4"
    narrator_script: "..."
  recoverable: true
```

### 13.3 Recuperación de Errores

Si la PC se apaga o hay un error:

1. Al reiniciar, el agente carga checkpoints pendientes
2. Pregunta al usuario: "¿Continuar tarea 'video_edit_123' (65% completada)?"
3. Si sí → reanuda desde el último checkpoint
4. Si no → marca como cancelada, limpia recursos

### 13.4 Scheduler de Tareas

```
┌─────────────────────────────────────────────┐
│           SCHEDULER DE G-MINI               │
├─────────────────────────────────────────────┤
│                                             │
│  [ ] Lunes 9:00 - Publicar en redes        │  ✅ Activo
│  [ ] Cada 6h - Revisar emails de leads     │  ✅ Activo
│  [ ] 24/7 - Jugar Clash hasta 10k          │  🔄 En progreso (8.2k)
│  [ ] Viernes 18:00 - Backup de archivos    │  ⏳ Pendiente
│                                             │
│  [+ Agregar tarea programada]               │
└─────────────────────────────────────────────┘
```

---

## 14. Sistema de Presupuesto y Recursos

El agente puede manejar dinero y recursos con límites configurables.

### 14.1 Cuentas y Métodos de Pago

El usuario registra sus cuentas/tarjetas para que el agente pueda usarlas:

```yaml
recursos:
  cuentas:
    - nombre: "Tarjeta BCP"
      tipo: "credit_card"
      limite_diario: 100  # Soles
      limite_mensual: 500
      uso: ["fb_ads", "google_ads", "compras_verificadas"]
    
    - nombre: "PayPal Personal"
      tipo: "paypal"
      email: "user@example.com"
      limite_transaccion: 50
      uso: ["freelance_tools", "subscriptions"]
  
  presupuestos:
    marketing_mensual: 200
    herramientas: 50
    emergencias: 100
```

### 14.2 Permisos de Gasto

| Nivel | Comportamiento |
|-------|---------------|
| Ninguno | No puede gastar nada, solo sugerir |
| Por-aprobación | Pide confirmación para cada gasto |
| Con-límite | Gasta libremente hasta el límite definido |
| Libre | Gasta según necesite (no recomendado) |

### 14.3 Flujo de Gasto

```
Tarea: "Crea campaña de FB Ads con 80 soles"
     │
     ├── Agente verifica presupuesto de marketing: 200 soles disponibles
     │
     ├── 80 soles < límite → Procede
     │
     ├── Agente crea campaña en FB Ads
     │
     ├── FB Ads cobra 80 soles de la tarjeta configurada
     │
     ├── Agente actualiza presupuesto: 200 - 80 = 120 soles restantes
     │
     └── Notifica: "Campaña creada. Gastado: S/80. Restante: S/120"
```

---

## 15. Restricciones Éticas y Legales

G-Mini Agent tiene capacidades poderosas, pero opera bajo restricciones configurables.

### 15.1 Restricciones Hardcodeadas (No modificables)

| Restricción | Razón |
|-------------|-------|
| No hackear sistemas externos sin autorización | Ilegal |
| No crear deepfakes de personas reales sin consentimiento | Ilegal/Ético |
| No comprar/vender sustancias ilegales | Ilegal |
| No generar CSAM ni contenido de abuso | Ilegal |
| No suplantar identidad para fraude | Ilegal |
| No violar derechos de autor masivamente | Ilegal |

### 15.2 Restricciones Configurables (Por el usuario)

```yaml
restricciones_usuario:
  # Seguridad
  confirmar_antes_de_pagar: true
  confirmar_antes_de_publicar: true  
  confirmar_antes_de_eliminar: true
  
  # Límites de tiempo
  max_horas_juego_dia: 4
  max_tiempo_redes_sociales: 2
  
  # Contenido
  filtrar_contenido_adulto: true
  idiomas_permitidos: ["es", "en"]
  
  # Acceso
  apps_bloqueadas: ["casino.exe", "apuestas.com"]
  sitios_bloqueados: ["xxx.com"]
  
  # Modo pentester (solo permitido si)
  pentester_solo_local: true
  pentester_requiere_source: true
```

### 15.3 Modo Pentester — Restricciones Especiales

El modo pentester **SOLO** puede auditar:
- ✅ Aplicaciones ejecutándose localmente en la PC del usuario
- ✅ Código fuente que el usuario posee
- ✅ Ambientes de desarrollo sin firmar
- ✅ Redes locales propias del usuario

**NO puede:**
- ❌ Atacar sistemas externos en producción
- ❌ Auditar apps sin consentimiento del dueño
- ❌ Realizar ataques DDoS
- ❌ Explotar vulnerabilidades en servicios públicos

### 15.4 Logging de Acciones Críticas

Todas las acciones sensibles se loguean:

```
[2026-03-05 14:30:22] ACTION: payment
  amount: 80 PEN
  destination: fb_ads
  authorized_by: user_preset (marketing budget)
  status: completed

[2026-03-05 15:45:10] ACTION: social_post
  platform: instagram
  content_type: image
  approved_by: whatsapp_confirm
  post_id: xxx

[2026-03-05 16:00:00] ACTION: file_delete
  path: /documents/old_backup.zip
  reason: user_command
  recoverable: true (in recycle bin)
```

---

## 16. Memoria a Largo Plazo (Memory System)

G-Mini no solo recuerda la conversación actual — **aprende y recuerda permanentemente** del usuario, sus preferencias, tareas pasadas y conocimiento acumulado.

### 16.1 Tipos de Memoria

| Tipo | Propósito | Ejemplo | Persistencia |
|------|-----------|---------|--------------|
| **Episódica** | Recordar tareas pasadas y cómo se resolvieron | "La última vez que edité un video, usé CapCut porque ffmpeg fallaba con ese codec" | Permanente |
| **Semántica** | Conocimiento acumulado sobre el usuario y su entorno | "El usuario tiene un negocio de internet llamado mi-negocio.com, vende en mi-ciudad" | Permanente |
| **Procedimental** | Workflows aprendidos por repetición | "Para publicar en los 19 perfiles: abrir Chrome perfil X → ir a FewFeed2 → cargar imagen..." | Permanente |
| **Contextual** | Preferencias implícitas detectadas | "El usuario prefiere que no le pida confirmación para tareas simples" | Se actualiza |
| **Corto plazo** | Conversación actual + buffers de trabajo | Chat actual, clipboard, última captura de pantalla | Sesión |

### 16.2 Arquitectura de Memoria

```
┌─────────────────────────────────────────────────────┐
│                   Memory Manager                     │
├──────────┬──────────┬──────────┬───────────────────┤
│ Episódica│ Semántica│Procedural│   Contextual      │
│          │          │          │                    │
│ ChromaDB │ ChromaDB │  JSON/   │  Perfil dinámico  │
│ vectors  │ vectors  │  YAML    │  actualizado       │
└──────────┴──────────┴──────────┴───────────────────┘
         ↕                    ↕
   Embeddings Model      Structured Storage
   (all-MiniLM-L6)       (SQLite / JSON)
```

**Motor de embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (local, sin API)
**Base vectorial:** ChromaDB o LanceDB (embebida, sin servidor externo)
**Storage estructurado:** SQLite para metadatos + JSON para workflows

### 16.3 Cómo Aprende

```python
class MemoryManager:
    def __init__(self):
        self.episodic = ChromaDB("memory/episodic")
        self.semantic = ChromaDB("memory/semantic")
        self.procedural = {}  # workflows aprendidos
        self.context_profile = {}  # preferencias del usuario
    
    async def remember_task(self, task: dict):
        """Guarda una tarea completada como memoria episódica"""
        embedding = self.embed(task['description'] + task['result'])
        self.episodic.add(
            documents=[json.dumps(task)],
            embeddings=[embedding],
            metadatas=[{
                'date': task['timestamp'],
                'mode': task['mode'],
                'success': task['success'],
                'tools_used': ','.join(task['tools_used'])
            }]
        )
    
    async def learn_about_user(self, fact: str, category: str):
        """Almacena conocimiento semántico sobre el usuario"""
        self.semantic.add(
            documents=[fact],
            metadatas=[{'category': category, 'date': now()}]
        )
    
    async def recall(self, query: str, memory_type: str = "all", top_k: int = 5):
        """Busca en la memoria relevante para el contexto actual"""
        results = []
        if memory_type in ("all", "episodic"):
            results += self.episodic.query(query, n_results=top_k)
        if memory_type in ("all", "semantic"):
            results += self.semantic.query(query, n_results=top_k)
        return self._rank_and_deduplicate(results)
    
    async def learn_workflow(self, name: str, steps: list):
        """Guarda un workflow aprendido como memoria procedimental"""
        self.procedural[name] = {
            'steps': steps,
            'times_executed': 0,
            'last_executed': None,
            'success_rate': 1.0
        }
```

### 16.4 Inyección de Memoria en el Prompt

Antes de cada llamada a la IA, el Memory Manager inyecta contexto relevante:

```python
async def build_context_with_memory(user_message: str):
    # Buscar memorias relevantes al mensaje actual
    memories = await memory_manager.recall(user_message, top_k=5)
    
    system_prompt_addition = ""
    if memories:
        system_prompt_addition = "\n## Memorias Relevantes:\n"
        for mem in memories:
            system_prompt_addition += f"- {mem['summary']}\n"
    
    # Inyectar perfil del usuario
    user_profile = memory_manager.get_user_profile()
    if user_profile:
        system_prompt_addition += f"\n## Sobre el usuario:\n{user_profile}\n"
    
    return system_prompt_addition
```

### 16.5 Comandos de Memoria

| Comando | Acción |
|---------|--------|
"G-Mini recuerda que mi negocio se llama MiNegocio" | Guarda en memoria semántica |
| "G-Mini ¿qué sabes de mí?" | Muestra perfil del usuario |
| "G-Mini ¿cómo hice lo de las publicaciones la semana pasada?" | Busca en memoria episódica |
| "G-Mini olvida todo sobre mi ex" | Borra memorias específicas |
| "G-Mini exporta tu memoria" | Exporta como JSON para backup |
| "G-Mini importa esta memoria" | Importa desde JSON |

### 16.6 Privacidad de la Memoria

- Toda la memoria es **100% local** (ChromaDB embebida)
- **Nunca se envía** a las APIs de IA (solo se inyecta en el prompt local)
- El usuario puede **ver, editar y borrar** cualquier memoria
- **Export/Import** para backup y migración entre dispositivos
- Opción de **memoria encriptada** con contraseña maestra

---

## 17. Grabación de Pantalla + Replay

G-Mini puede **grabar sesiones completas** de lo que hace en pantalla para auditoría, debugging y entrenamiento.

### 17.1 Modos de Grabación

| Modo | Descripción | Uso Principal |
|------|-------------|---------------|
| **Auto-Record** | Graba automáticamente cuando el agente ejecuta tareas | Auditoría y debugging |
| **Manual** | El usuario activa/desactiva la grabación | Documentación, demos |
| **Replay** | Reproduce una grabación pasada paso a paso | Entrenamiento, revisión |
| **Highlight Reel** | Genera un resumen acelerado de la sesión | Reportes rápidos |

### 17.2 Qué Se Graba

```python
class SessionRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.events = []  # clicks, teclado, navegación
    
    async def start_recording(self, task_id: str):
        """Inicia grabación vinculada a una tarea"""
        self.recording = True
        self.current_session = {
            'task_id': task_id,
            'start_time': datetime.now(),
            'frames': [],
            'events': [],
            'metadata': {}
        }
    
    async def capture_frame(self):
        """Captura frame con metadatos"""
        screenshot = mss.mss().grab(monitor)
        self.current_session['frames'].append({
            'timestamp': time.time(),
            'image': compress_png(screenshot),
            'active_window': get_active_window_title(),
            'mouse_pos': pyautogui.position()
        })
    
    async def log_event(self, event_type: str, details: dict):
        """Registra un evento de automatización"""
        self.current_session['events'].append({
            'timestamp': time.time(),
            'type': event_type,  # click, type, scroll, navigate
            'details': details,
            'reasoning': details.get('agent_reasoning', '')
        })
    
    async def stop_and_save(self) -> str:
        """Detiene y guarda la grabación"""
        self.recording = False
        session_file = f"recordings/{self.current_session['task_id']}.gmrec"
        save_compressed(self.current_session, session_file)
        return session_file
```

### 17.3 Reproductor de Sesiones

```
┌──────────────────────────────────────────────────────┐
│  📹 Reproductor de Sesión                    [✕]     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────────────────────────────────┐     │
│  │                                              │     │
│  │         [Captura de pantalla frame]          │     │
│  │                                              │     │
│  │    🔴 Click en (450, 320)                   │     │
│  │    💭 "Hago click en el botón Publicar"     │     │
│  │                                              │     │
│  └─────────────────────────────────────────────┘     │
│                                                       │
│  ◄◄  ◄  ▶  ►  ►►    ⏱️ 2:34 / 15:20               │
│  ─────●──────────────────────────────── 1x  2x  4x  │
│                                                       │
│  📋 Eventos: [Click][Type][Navigate][Screenshot]...  │
│                                                       │
│  💬 Razonamiento del agente:                          │
│  "Navego a Instagram porque el usuario pidió          │
│   publicar el carousel en sus 19 perfiles"            │
└──────────────────────────────────────────────────────┘
```

### 17.4 Comandos de Grabación

| Comando | Acción |
|---------|--------|
| "G-Mini graba lo que vas a hacer" | Activa grabación manual |
| "G-Mini deja de grabar" | Detiene y guarda |
| "G-Mini muéstrame qué hiciste ayer con Instagram" | Abre replay de esa sesión |
| "G-Mini ¿por qué hiciste click ahí?" | Muestra razonamiento del agente en ese paso |
| "G-Mini haz un resumen en video de lo que hiciste" | Genera highlight reel acelerado |

### 17.5 Almacenamiento

```yaml
recordings:
  storage_path: "data/recordings/"
  format: ".gmrec"  # formato comprimido propietario
  compression: "zstd"  # Zstandard para alta compresión
  retention:
    auto_records: "30 días"  # Grabaciones automáticas se borran después de 30 días
    manual_records: "indefinido"  # Las manuales se mantienen
    max_storage: "10 GB"  # Límite de espacio
  capture_fps: 2  # 2 frames por segundo (suficiente para replay)
  include_reasoning: true  # Incluir razonamiento del agente
```

---

## 18. Macros / Workflows Grabables (RPA)

El usuario realiza una tarea manualmente **una sola vez** y G-Mini la aprende como macro reutilizable.

### 18.1 Grabación de Macros

```
Usuario: "G-Mini, graba lo que voy a hacer"

G-Mini: "📹 Grabando tus acciones. Hazlo normalmente, yo observo."

→ Usuario abre Chrome
→ Navega a facebook.com/groups/mi-grupo-ventas
→ Click en "Crear publicación"
→ Escribe "Vendo internet fibra óptica..."
→ Adjunta imagen poster.png
→ Click en "Publicar"

Usuario: "G-Mini, para de grabar. Llama a esto 'publicar en grupo Juliaca'"

G-Mini: "✅ Macro 'publicar en grupo Juliaca' guardada con 6 pasos:
  1. Abrir Chrome
  2. Navegar a facebook.com/groups/ventas-juliaca
  3. Click en 'Crear publicación'
  4. Escribir texto de publicación
  5. Adjuntar imagen
  6. Click en 'Publicar'
  
  ¿La configuro como tarea recurrente?"
```

### 18.2 Estructura de una Macro

```yaml
macro:
  name: "publicar en grupo Juliaca"
  id: "macro_publicar_juliaca"
  recorded_date: "2026-03-05"
  
  # Variables dinámicas (el agente las detecta automáticamente)
  variables:
    - name: "texto_publicacion"
      type: "string"
      default: "Vendo internet fibra óptica..."
      description: "Texto del post"
    - name: "imagen"
      type: "file"
      default: "poster.png"
      description: "Imagen a adjuntar"
  
  steps:
    - action: "open_app"
      target: "chrome"
      profile: "auto"
    
    - action: "navigate"
      url: "facebook.com/groups/ventas-juliaca"
    
    - action: "click"
      target: "Crear publicación"
      method: "vision"  # Encuentra el botón por OCR/visión
    
    - action: "type"
      text: "${texto_publicacion}"
      target: "campo de texto activo"
    
    - action: "attach_file"
      file: "${imagen}"
    
    - action: "click"
      target: "Publicar"
      wait_after: 3000  # Esperar 3s después de publicar
  
  # Configuración de ejecución
  execution:
    speed: "normal"  # slow, normal, fast
    error_handling: "pause_and_ask"
    retry_on_fail: true
    max_retries: 2
```

### 18.3 Editar y Parametrizar Macros

El agente es inteligente: al grabar, **detecta automáticamente** qué partes son variables:

```python
class MacroIntelligence:
    async def analyze_recorded_steps(self, steps: list) -> dict:
        """Analiza los pasos grabados y detecta variables"""
        variables = []
        
        for step in steps:
            if step['action'] == 'type':
                # El texto escrito probablemente cambia cada vez
                variables.append({
                    'name': self._suggest_var_name(step),
                    'type': 'string',
                    'default': step['text'],
                    'step_index': step['index']
                })
            
            if step['action'] == 'attach_file':
                # El archivo adjunto probablemente cambia
                variables.append({
                    'name': 'archivo_adjunto',
                    'type': 'file',
                    'default': step['file'],
                    'step_index': step['index']
                })
        
        return {'variables': variables, 'steps': steps}
```

### 18.4 Ejecutar Macros

```
Usuario: "G-Mini ejecuta la macro 'publicar en grupo Juliaca' 
          con el texto 'Nuevo plan de 100Mbps a solo S/59' 
          y la imagen promo_marzo.png"

G-Mini: "▶️ Ejecutando macro 'publicar en grupo Juliaca'...
  ✅ Paso 1/6: Chrome abierto
  ✅ Paso 2/6: Navegando a grupo...
  ✅ Paso 3/6: Campo de publicación abierto
  ✅ Paso 4/6: Texto escrito
  ✅ Paso 5/6: Imagen adjuntada
  ✅ Paso 6/6: ¡Publicado!
  
  Macro completada en 12 segundos."
```

### 18.5 Diferencia entre Macros y Skills

| Característica | Macros | Skills |
|---------------|--------|--------|
| Creación | Grabadas por el usuario | Programadas en código |
| Complejidad | Secuencia lineal de pasos | Lógica compleja con condicionales |
| Adaptabilidad | Reproduce exactamente lo grabado | Se adapta al contexto |
| Distribución | Exportables como .yaml | Marketplace de plugins |
| Mantenimiento | Si la UI cambia, puede fallar | Más resiliente a cambios |

---

## 19. Sistema de Rollback / Undo

Si G-Mini comete un error, puede **revertir automáticamente** sus acciones.

### 19.1 Registro de Acciones Reversibles

```python
class ActionHistory:
    def __init__(self):
        self.history = []  # Pila de acciones
    
    async def record_action(self, action: dict):
        """Registra cada acción con su método de reversión"""
        reverse_info = await self._compute_reverse(action)
        self.history.append({
            'action': action,
            'timestamp': datetime.now(),
            'reverse_method': reverse_info,
            'state_snapshot': await self._snapshot_state(action)
        })
    
    async def undo_last(self, n: int = 1) -> list:
        """Revierte las últimas N acciones"""
        results = []
        for _ in range(n):
            if not self.history:
                break
            entry = self.history.pop()
            result = await self._execute_reverse(entry)
            results.append(result)
        return results
```

### 19.2 Tabla de Reversiones

| Acción del Agente | Método de Rollback | Automático |
|-------------------|-------------------|------------|
| Borrar archivo | Recuperar de papelera de reciclaje | ✅ |
| Mover archivo | Mover de vuelta a ubicación original | ✅ |
| Renombrar archivo | Renombrar con nombre original | ✅ |
| Escribir texto | Ctrl+Z (undo nativo) × N veces | ✅ |
| Publicar en red social | Eliminar/archivar el post | ✅ (si la API lo permite) |
| Enviar email | No reversible, pero alerta inmediata | ⚠️ Con delay configurable |
| Modificar configuración | Restaurar backup automático previo | ✅ |
| Instalar programa | Desinstalar | ✅ |
| Crear archivo | Eliminar archivo creado | ✅ |
| Cerrar app sin guardar | Restaurar desde autosave si existe | ⚠️ Parcial |
| Ejecutar comando terminal | Depende del comando (algunos irreversibles) | ⚠️ Caso por caso |
| Transacción financiera | No reversible — requirió aprobación previa | ❌ Irreversible |

### 19.3 Backup Automático Pre-Acción

Antes de cualquier acción destructiva, G-Mini crea un **snapshot**:

```python
class SafetyBackup:
    async def pre_action_backup(self, action: dict):
        """Crea backup antes de acciones peligrosas"""
        if action['risk_level'] >= 'medium':
            if action['type'] == 'file_modify':
                # Copiar archivo antes de modificar
                shutil.copy2(action['target'], 
                            f"backups/{timestamp}_{basename(action['target'])}")
            
            elif action['type'] == 'config_change':
                # Snapshot de la configuración actual
                save_config_snapshot(f"backups/config_{timestamp}.json")
            
            elif action['type'] == 'registry_edit':
                # Exportar clave del registro antes de modificar
                export_registry_key(action['key'], 
                                   f"backups/reg_{timestamp}.reg")
```

### 19.4 Comandos de Rollback

| Comando | Acción |
|---------|--------|
| "G-Mini deshaz lo último" | Revierte la última acción |
| "G-Mini deshaz las últimas 5 acciones" | Revierte las últimas 5 |
| "G-Mini deshaz todo lo que hiciste hoy" | Revierte todas las acciones del día |
| "G-Mini ¿qué puedes deshacer?" | Muestra historial de acciones reversibles |
| "G-Mini restaura el archivo X a como estaba antes" | Restaura desde backup |

### 19.5 Confirmación con Delay para Acciones Críticas

Para acciones irreversibles, G-Mini implementa un **delay inteligente**:

```
G-Mini: "📧 Email listo para enviar a 500 contactos.
         Enviando en 10 segundos...
         
         [Cancelar envío] [Enviar ahora]
         
         ⏱️ 10... 9... 8..."
```

Si el usuario no cancela en el delay, se ejecuta. El delay es configurable por tipo de acción.

---

## 20. Analytics del Agente (Dashboard de Rendimiento)

Un dashboard completo que muestra **métricas de uso, rendimiento y costos** del agente.

### 20.1 Métricas Recopiladas

```python
class AgentAnalytics:
    metrics = {
        # Uso de IA
        'tokens_consumed': {},        # Por proveedor, por día
        'api_calls': {},              # Cantidad de llamadas
        'api_costs': {},              # Costo en USD por proveedor
        'model_usage': {},            # Qué modelo se usa más
        
        # Rendimiento de tareas
        'tasks_completed': 0,
        'tasks_failed': 0,
        'avg_task_duration': 0,
        'success_rate': 0.0,
        
        # Automatización
        'actions_performed': {},      # clicks, types, navigations
        'screens_captured': 0,
        'macros_executed': 0,
        
        # Recursos del sistema
        'cpu_usage_avg': 0,
        'ram_usage_avg': 0,
        'gpu_usage_avg': 0,
        
        # Canales
        'messages_received': {},      # Por canal
        'messages_sent': {},
        'response_time_avg': {},
    }
```

### 20.2 Dashboard Visual

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Analytics de G-Mini Agent         Período: [Esta semana▼]│
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  💰 Costos                    📈 Tareas                      │
│  ┌─────────────┐              ┌─────────────┐               │
│  │ $12.45 USD  │              │    95.2%     │               │
│  │ esta semana │              │  success rate│               │
│  │ ▁▂▃▅▇█▇▅▃  │              │ 142 exitosas │               │
│  │ L M X J V  │              │   7 fallidas │               │
│  └─────────────┘              └─────────────┘               │
│                                                               │
│  🤖 Tokens por Proveedor        ⏱️ Tiempo Promedio          │
│  ┌─────────────────────┐        ┌──────────────┐           │
│  │ Claude   ████░ 45%  │        │ Simple: 8s   │           │
│  │ GPT-5    ███░░ 30%  │        │ Media:  45s  │           │
│  │ Gemini   ██░░░ 15%  │        │ Compleja: 5m │           │
│  │ Ollama   █░░░░ 10%  │        │              │           │
│  └─────────────────────┘        └──────────────┘           │
│                                                               │
│  🔥 Top 5 Acciones del Agente      📱 Mensajes por Canal    │
│  1. Click (2,340 veces)            WhatsApp: 89             │
│  2. Type (1,890 veces)             Discord: 45              │
│  3. Navigate (567 veces)           Telegram: 23             │
│  4. Screenshot (445 veces)         Slack: 12                │
│  5. File operation (234 veces)     SMS: 5                   │
│                                                               │
│  ⚠️ Errores Frecuentes                                      │
│  • Timeout en Facebook (12 veces) → Sugerencia: aumentar    │
│  • OCR falló en modo oscuro (8 veces) → Sugerencia: modo 3  │
│  • Captcha bloqueó acción (5 veces) → Sugerencia: 2captcha  │
└──────────────────────────────────────────────────────────────┘
```

### 20.3 Exportación de Reportes

| Formato | Contenido |
|---------|-----------|
| **PDF** | Reporte visual con gráficas |
| **CSV** | Datos crudos para análisis |
| **JSON** | Datos estructurados para integración |
| **Canvas** | Dashboard interactivo en el Canvas de G-Mini |

---

## 21. Clipboard Inteligente (Multi-Clipboard)

G-Mini mantiene un **historial completo del portapapeles** con categorización y búsqueda.

### 21.1 Funcionalidades

```python
class SmartClipboard:
    def __init__(self):
        self.history = []  # Hasta 500 items
        self.pinned = []   # Items fijados
        self.categories = {
            'text': [], 'image': [], 'url': [], 
            'code': [], 'file_path': [], 'color': []
        }
    
    async def on_clipboard_change(self, content):
        """Se ejecuta cada vez que el usuario copia algo"""
        item = {
            'content': content,
            'type': self._detect_type(content),
            'timestamp': datetime.now(),
            'source_app': get_active_window_title(),
            'preview': self._generate_preview(content)
        }
        self.history.insert(0, item)
        self.categories[item['type']].append(item)
        
        # Truncar si excede el límite
        if len(self.history) > 500:
            self.history.pop()
    
    def _detect_type(self, content) -> str:
        """Detecta automáticamente el tipo de contenido"""
        if is_url(content): return 'url'
        if is_color_code(content): return 'color'
        if is_file_path(content): return 'file_path'
        if looks_like_code(content): return 'code'
        if isinstance(content, Image): return 'image'
        return 'text'
    
    async def search(self, query: str) -> list:
        """Busca en el historial del clipboard"""
        return [item for item in self.history 
                if query.lower() in str(item['content']).lower()]
    
    async def paste_from_history(self, index: int):
        """Pega un item específico del historial"""
        item = self.history[index]
        pyperclip.copy(item['content'])
        pyautogui.hotkey('ctrl', 'v')
```

### 21.2 UI del Clipboard

```
┌──────────────────────────────────────────┐
│  📋 Clipboard Inteligente    [🔍 Buscar] │
├──────────────────────────────────────────┤
│ [Todo] [Texto] [URLs] [Código] [Imgs]   │
│                                           │
│ 📌 Fijados:                              │
│  • "ARG-2026-0542" (código de pedido)     │
│  • "192.168.1.1" (IP del router)         │
│                                           │
│ Recientes:                                │
│  1. "npm install express" — VS Code, 2m  │
│  2. "https://github.com/..." — Chrome, 5m│
│  3. [Imagen 800x600] — Photoshop, 10m    │
│  4. "SELECT * FROM users..." — DBeaver   │
│  5. "Hola, te envío la cotización..."    │
│                                           │
│ [📱 Sync con Nodes] [🗑️ Limpiar historial]│
└──────────────────────────────────────────┘
```

### 21.3 Sincronización entre Dispositivos

El clipboard se sincroniza con otros nodes (dispositivos) conectados:
- Copiar en PC → pegar en celular
- Copiar en celular → pegar en PC
- Vía WebSocket encriptado entre nodes

### 21.4 Comandos

| Comando | Acción |
|---------|--------|
| "G-Mini ¿qué copié hace rato del navegador?" | Busca en historial por fuente |
| "G-Mini pega lo que copié de VS Code" | Pega el último item de VS Code |
| "G-Mini fija este texto en el clipboard" | Pin del item actual |
| "G-Mini envía mi clipboard al celular" | Sync con node móvil |

---

## 22. Bandeja de Entrada Unificada

Un panel que **agrupa todas las notificaciones y mensajes** de todos los canales en un solo lugar.

### 22.1 Fuentes de Notificaciones

| Fuente | Tipo | Ejemplo |
|--------|------|---------|
| **Gmail / Outlook** | Email | "Nueva factura de proveedor" |
| **WhatsApp** | Mensaje | "Juan: ¿ya subiste el post?" |
| **Discord** | Mención | "@G-Mini revisa el servidor" |
| **Telegram** | Mensaje | "Nuevo pedido en el bot" |
| **Slack** | Canal | "#ventas: nuevo lead" |
| **GitHub** | PR/Issue | "PR #45 aprobado, listo para merge" |
| **Shopify/WooCommerce** | Venta | "Nueva venta: $45.00" |
| **FB Ads / Google Ads** | Alerta | "Presupuesto diario al 80%" |
| **Sistema** | Evento | "Actualización disponible" |
| **Cron/Tareas** | Resultado | "Tarea 'backup' completada" |

### 22.2 Interfaz de Bandeja

```
┌──────────────────────────────────────────────────────┐
│  📬 Bandeja Unificada                [Filtrar ▼] [⚙️]│
├──────────────────────────────────────────────────────┤
│                                                       │
│ 🔴 Alta Prioridad:                                   │
│  📧 Gmail: "URGENTE: Factura vencida" — hace 5min    │
│     → [Responder] [Marcar leído] [Pedir a G-Mini]   │
│                                                       │
│  💬 WhatsApp: Juan dice "¿ya subiste el post?"       │
│     → [Responder] [G-Mini responde] [Ignorar]       │
│                                                       │
│ 🟡 Normal:                                            │
│  🔔 Discord: @mencion en #trabajo — hace 15min       │
│     → [Ver en Discord] [G-Mini responde]             │
│                                                       │
│  🛒 Shopify: Nueva venta por $45.00 — hace 20min    │
│     → [Ver pedido] [G-Mini procesa envío]            │
│                                                       │
│  📊 FB Ads: Campaña "Marzo" alcanzó 10k — hace 1h   │
│     → [Ver métricas] [Ajustar presupuesto]           │
│                                                       │
│ ⚪ Informativas:                                      │
│  ✅ Cron: Backup diario completado — hace 2h         │
│  📱 Sistema: Actualización v2.3 disponible           │
│                                                       │
│ ─────────────────────────────────────────────         │
│ Resumen: 8 sin leer | 2 urgentes | 12 hoy           │
└──────────────────────────────────────────────────────┘
```

### 22.3 Acciones Inteligentes

El agente puede **actuar directamente** desde la bandeja:

```
Usuario: "G-Mini, responde a Juan que ya lo subí y envía 
          el link del post"

G-Mini: "✅ Respondido a Juan por WhatsApp:
         'Ya lo subí! Aquí está el link: [fb.com/post/...]'"
```

O en modo automático:
```yaml
inbox_rules:
  - when: "email contains 'factura'"
    action: "forward_to_accountant"
    
  - when: "whatsapp from 'jefe' and contains '?'"
    priority: "high"
    notify: "tts"  # Leer en voz alta
    
  - when: "shopify new_order"
    action: "run_macro('procesar_pedido')"
    
  - when: "github pr_approved"
    action: "git merge and deploy"
```

---

## 23. Modo Test / Dry Run

Antes de ejecutar tareas complejas, G-Mini puede hacer un **simulacro completo** sin ejecutar nada.

### 23.1 Cómo Funciona

```python
class DryRunEngine:
    def __init__(self):
        self.simulated_steps = []
        self.dry_run_mode = False
    
    async def simulate_task(self, task: dict) -> dict:
        """Simula una tarea completa sin ejecutar"""
        self.dry_run_mode = True
        self.simulated_steps = []
        
        # El agente planifica como si fuera real
        plan = await agent.plan_task(task)
        
        for step in plan['steps']:
            # En vez de ejecutar, solo registra qué haría
            simulation = {
                'step_number': step['index'],
                'action': step['action'],
                'target': step['target'],
                'would_succeed': await self._predict_success(step),
                'estimated_time': step.get('estimated_time', '?'),
                'risks': await self._assess_risks(step),
                'cost': step.get('estimated_cost', 0)
            }
            self.simulated_steps.append(simulation)
        
        self.dry_run_mode = False
        
        return {
            'total_steps': len(self.simulated_steps),
            'estimated_time': sum(s['estimated_time'] for s in self.simulated_steps),
            'estimated_cost': sum(s['cost'] for s in self.simulated_steps),
            'potential_risks': [s for s in self.simulated_steps if s['risks']],
            'success_probability': self._calculate_probability(),
            'steps': self.simulated_steps
        }
```

### 23.2 Ejemplo de Dry Run

```
Usuario: "G-Mini, haz un dry run de publicar en mis 19 perfiles"

G-Mini: "🧪 DRY RUN — Simulación sin ejecutar:

  📋 Plan: 19 publicaciones en 19 perfiles de Chrome
  
  Paso  1: Abrir Chrome perfil 'Juliaca'        ✅ Viable
  Paso  2: Navegar a FewFeed2                    ✅ Viable
  Paso  3: Cargar imagen poster.png              ✅ Viable
  Paso  4: Configurar 3 grupos de Facebook       ✅ Viable
  Paso  5: Click en 'Publicar'                   ✅ Viable
  ...
  Paso 56: Cerrar último perfil                  ✅ Viable
  
  📊 Resumen:
  • Total pasos: 56
  • Tiempo estimado: ~18 minutos
  • Costo: $0.05 (tokens de IA)
  • Probabilidad de éxito: 94%
  
  ⚠️ Riesgos detectados:
  • Perfil 'Tacna' no se usó en 15 días (posible logout)
  • Facebook puede pedir verificación después del perfil #12
  
  ¿Ejecutar de verdad? [Sí] [No] [Modificar plan]"
```

### 23.3 Comandos de Dry Run

| Comando | Acción |
|---------|--------|
| "G-Mini haz un dry run de..." | Simula la tarea sin ejecutar |
| "G-Mini prueba primero antes de hacer..." | Activa dry run automático |
| "G-Mini siempre haz dry run para tareas largas" | Configura dry run automático |
| "G-Mini, el dry run se ve bien, dale" | Ejecuta después de ver simulación |

---

## 24. Proxy / VPN Manager

Para tareas que requieren múltiples identidades o geo-localizaciones.

### 24.1 Casos de Uso

| Escenario | Necesidad | Solución |
|-----------|-----------|----------|
| Múltiples perfiles de Facebook | Evitar ban por misma IP | Proxy diferente por perfil |
| Scraping de precios | Sitios que bloquean por IP | Rotación automática de proxies |
| Publicar desde diferentes ciudades | Geo-targeting | Proxy residencial por ciudad |
| Verificar ads en otro país | Ver cómo se muestra tu ad | VPN temporal a ese país |
| Acceder a contenido geo-bloqueado | El sitio solo funciona en USA | Proxy USA |

### 24.2 Configuración de Proxies

```yaml
proxy_manager:
  enabled: true
  
  # Pool de proxies
  proxies:
    - id: "proxy_juliaca"
      type: "residential"
      provider: "brightdata"  # o smartproxy, oxylabs, etc.
      host: "brd.superproxy.io"
      port: 22225
      username: "user-country-pe-city-juliaca"
      password: "***"
      assigned_to: ["chrome_perfil_juliaca", "chrome_perfil_juliaca2"]
    
    - id: "proxy_lima"
      type: "residential"
      provider: "brightdata"
      host: "brd.superproxy.io"
      port: 22225
      username: "user-country-pe-city-lima"
      password: "***"
      assigned_to: ["chrome_perfil_lima"]
    
    - id: "proxy_usa"
      type: "datacenter"
      host: "us-proxy.example.com"
      port: 8080
      use_for: ["scraping", "geo_check"]
  
  # Rotación automática
  rotation:
    strategy: "round_robin"  # o random, sticky, least_used
    rotate_on_error: true
    rotate_on_captcha: true
    cooldown_after_ban: 300  # 5 min de cooldown si detecta ban
  
  # VPN (opcional)
  vpn:
    provider: "wireguard"  # o openvpn, nordvpn-cli
    configs_folder: "config/vpn/"
    auto_connect: false
```

### 24.3 Asignación Inteligente

El agente decide automáticamente qué proxy usar:

```python
class ProxyManager:
    async def get_proxy_for_task(self, task: dict) -> dict:
        """Selecciona el proxy óptimo para la tarea"""
        if task.get('chrome_profile'):
            # Usar proxy asignado al perfil
            return self.get_assigned_proxy(task['chrome_profile'])
        
        if task.get('target_country'):
            # Usar proxy del país objetivo
            return self.get_proxy_by_country(task['target_country'])
        
        if task.get('needs_rotation'):
            # Usar siguiente proxy en rotación
            return self.get_next_in_rotation()
        
        # Sin proxy si no es necesario
        return None
```

---

## 25. Notificaciones Inteligentes con Prioridad

No todas las notificaciones son iguales. G-Mini **clasifica y entrega** notificaciones según su importancia.

### 25.1 Niveles de Prioridad

| Nivel | Comportamiento | Ejemplo | Interrupción |
|-------|---------------|---------|--------------|
| 🔴 **Crítica** | Push + sonido fuerte + TTS inmediato + parpadeo del personaje | "Tu servidor web está caído" | Sí, interrumpe todo |
| 🟡 **Alta** | Push + sonido suave + badge en personaje | "Campaña de ads terminó presupuesto" | Solo si está idle |
| 🔵 **Normal** | Push silenciosa + badge | "Video exportado correctamente" | No interrumpe |
| ⚪ **Baja** | Solo log, no notifica visualmente | "Checkpoint de backup guardado" | Nunca |

### 25.2 Clasificación Automática

```python
class NotificationClassifier:
    # Reglas hardcodeadas
    CRITICAL_KEYWORDS = ['caído', 'error crítico', 'hackeado', 'eliminado', 
                         'dinero', 'factura vencida', 'urgente']
    
    async def classify(self, notification: dict) -> str:
        """Clasifica la prioridad de una notificación"""
        # Reglas del usuario primero
        user_rule = self.check_user_rules(notification)
        if user_rule:
            return user_rule
        
        # Reglas hardcodeadas
        if any(kw in notification['text'].lower() for kw in self.CRITICAL_KEYWORDS):
            return 'critical'
        
        # IA clasifica si no hay regla clara
        classification = await ai.classify_priority(notification)
        
        # Aprender de las reacciones del usuario
        # Si el usuario ignora notificaciones "alta", bajar a "normal"
        return self.adjust_by_user_behavior(classification)
```

### 25.3 Configuración

```yaml
notifications:
  # Comportamiento por prioridad
  critical:
    sound: "alert_urgent.wav"
    tts: true  # Leer en voz alta
    flash_character: true
    send_to_phone: true  # Push a WhatsApp/Telegram
    
  high:
    sound: "notification.wav"
    tts: false
    badge: true
    
  normal:
    sound: null
    badge: true
    
  low:
    sound: null
    badge: false
    log_only: true
  
  # Modo No Molestar
  dnd:
    enabled: false
    schedule: "23:00-07:00"
    allow_critical: true  # Críticas pasan aunque esté en DND
  
  # Agrupación
  grouping:
    same_source_interval: 60  # Agrupar del mismo origen si llegan en 60s
    max_per_minute: 5  # Máximo 5 notificaciones por minuto
```

### 25.4 Aprendizaje de Prioridad

G-Mini **aprende** qué es importante observando el comportamiento del usuario:
- Si el usuario siempre abre emails de "X persona" inmediatamente → subir prioridad
- Si el usuario ignora notificaciones de "canal Y" → bajar prioridad
- Si el usuario responde rápido a cierto tipo de mensaje → marcar como alta prioridad

---

## 26. Handoff Humano (Human-in-the-Loop)

Cuando G-Mini no puede resolver algo, **escala al humano** de forma inteligente.

### 26.1 Escenarios de Escalación

| Situación | Comportamiento del Agente |
|-----------|--------------------------|
| **Captcha** | Muestra el captcha al usuario o usa servicio externo |
| **Decisión ambigua** | "Encontré 3 opciones, ¿cuál prefieres?" |
| **Error inesperado** | "No pude hacer X, ¿lo intentas manualmente?" |
| **Verificación 2FA** | "Te llegó un código al celular, ¿me lo das?" |
| **Límite de confianza** | "No estoy seguro de si esto es correcto, ¿verificas?" |
| **Dato faltante** | "Necesito tu dirección para completar el formulario" |
| **Pago no autorizado** | "Este sitio pide pago de $X, ¿autorizo?" |

### 26.2 Flujo de Escalación

```python
class HumanHandoff:
    async def escalate(self, reason: str, context: dict, options: list = None):
        """Escala una decisión al humano"""
        
        # 1. Notificar por el canal más rápido
        notification = {
            'type': 'handoff',
            'reason': reason,
            'context': context,
            'options': options or ['Resolver manualmente', 'Reintentar', 'Cancelar'],
            'screenshot': await capture_current_state(),
            'urgency': self._assess_urgency(context)
        }
        
        # 2. Intentar por orden de velocidad
        response = None
        
        # Primero: UI local (si el usuario está en la PC)
        if user_is_at_pc():
            response = await self.show_popup(notification)
        
        # Segundo: Personaje habla con TTS
        if not response:
            await tts.speak(f"Necesito tu ayuda: {reason}")
        
        # Tercero: WhatsApp/Telegram (si no responde en 30s)
        if not response:
            response = await self.send_to_channels(notification, timeout=120)
        
        # Cuarto: Pausar tarea y esperar
        if not response:
            await self.pause_task(context['task_id'])
            return {'status': 'paused', 'reason': 'waiting_for_human'}
        
        return response
```

### 26.3 Captcha Handling

```
G-Mini: "🔐 Encontré un captcha que no puedo resolver.
         
         [Imagen del captcha]
         
         Opciones:
         1. [Resuélvelo tú] → Te muestro la ventana
         2. [Usar 2Captcha] → Servicio externo ($0.003)
         3. [Usar Anti-Captcha] → Servicio externo ($0.002)
         4. [Intentar otro método] → Busco bypass alternativo
         5. [Cancelar tarea]"
```

### 26.4 Configuración de Handoff

```yaml
handoff:
  # Cuándo escalar automáticamente
  auto_escalate:
    on_captcha: true
    on_2fa: true
    on_payment: true
    on_ambiguity: true
    confidence_threshold: 0.6  # Si confianza < 60%, preguntar
  
  # Servicios de resolución de captcha
  captcha_services:
    - name: "2captcha"
      api_key: "***"
      enabled: true
    - name: "anti-captcha"
      api_key: "***"
      enabled: false
  
  # Timeout antes de pausar
  human_response_timeout: 300  # 5 minutos
  
  # Acción si no responde
  on_timeout: "pause"  # pause, skip, cancel, retry
```

---

## 27. Vault de Credenciales

Un gestor de contraseñas **cifrado e integrado** que G-Mini usa para auto-loguearse en servicios.

### 27.1 Arquitectura de Seguridad

```
┌─────────────────────────────────────┐
│          Vault Manager               │
├─────────────────────────────────────┤
│  🔐 Master Password (PBKDF2)       │
│     ↓                               │
│  🔑 Derived Key (AES-256-GCM)      │
│     ↓                               │
│  📦 Encrypted Storage               │
│     ├── credentials.vault           │
│     ├── api_keys.vault              │
│     └── totp_secrets.vault          │
└─────────────────────────────────────┘
```

**Todo el vault se cifra con AES-256-GCM** derivado de la contraseña maestra del usuario.

### 27.2 Tipos de Credenciales

```yaml
vault:
  # Cuentas web
  credentials:
    facebook_principal:
      type: "web_login"
      url: "facebook.com"
      email: "user@email.com"
      password: "***encrypted***"
      2fa_method: "totp"
      totp_secret: "***encrypted***"
      chrome_profile: "perfil_principal"
    
    instagram_negocio:
      type: "web_login"
      url: "instagram.com"
      email: "negocio@example.com"
      password: "***encrypted***"
      2fa_method: "sms"
      phone: "+51XXXXXXXXX"
    
    hosting_vps:
      type: "ssh"
      host: "123.45.67.89"
      port: 22
      user: "admin"
      auth: "ssh_key"
      ssh_key: "~/.ssh/vps_key"
    
    database_produccion:
      type: "database"
      engine: "postgresql"
      host: "db.example.com"
      port: 5432
      user: "app_user"
      password: "***encrypted***"
      database: "produccion"
  
  # API Keys
  api_keys:
    openai: "***encrypted***"
    anthropic: "***encrypted***"
    google_gemini: "***encrypted***"
    stripe: "***encrypted***"
    twilio: "***encrypted***"
```

### 27.3 Auto-Login Inteligente

```python
class VaultAutoLogin:
    async def login_to_service(self, service_id: str):
        """Auto-login completo incluyendo 2FA"""
        cred = vault.get_credential(service_id)
        
        # 1. Navegar al login
        await browser.navigate(cred['url'] + '/login')
        
        # 2. Ingresar credenciales
        await browser.type_in_field('email', cred['email'])
        await browser.type_in_field('password', vault.decrypt(cred['password']))
        await browser.click('Login')
        
        # 3. Manejar 2FA si es necesario
        if cred.get('2fa_method') == 'totp':
            code = pyotp.TOTP(vault.decrypt(cred['totp_secret'])).now()
            await browser.type_in_field('2fa_code', code)
            await browser.click('Verify')
        
        elif cred.get('2fa_method') == 'sms':
            # Esperar que el usuario proporcione el código
            code = await handoff.ask_human("Ingresa el código SMS de 2FA")
            await browser.type_in_field('2fa_code', code)
            await browser.click('Verify')
        
        return {'success': True, 'service': service_id}
```

### 27.4 Comandos del Vault

| Comando | Acción |
|---------|--------|
| "G-Mini guarda estas credenciales" | Agrega al vault |
| "G-Mini logueate en Facebook con mi cuenta principal" | Auto-login |
| "G-Mini muéstrame la contraseña de Instagram" | Requiere master password |
| "G-Mini genera una contraseña segura" | Genera y guarda password aleatorio |
| "G-Mini exporta mi vault" | Exporta cifrado para backup |
| "G-Mini rota la contraseña de hosting" | Cambia password y actualiza vault |

---

## 28. A/B Testing Automático

Para tareas de marketing, G-Mini puede crear, ejecutar y analizar **pruebas A/B** automáticamente.

### 28.1 Flujo de A/B Testing

```
Usuario: "G-Mini, haz un A/B test del post de internet.
          Prueba dos textos diferentes"

G-Mini: "🧪 Creando A/B Test:
  
  Variante A: 'Internet fibra óptica 100Mbps a solo S/59/mes'
  Variante B: '¿Cansado del internet lento? Prueba fibra a S/59'
  
  📊 Plan:
  • Publicar A en 10 grupos aleatorios
  • Publicar B en los otros 9 grupos
  • Monitorear engagement por 48 horas
  • Declarar ganador basado en reacciones + comentarios
  
  ¿Procedo?"
```

### 28.2 Tipos de Tests

| Tipo | Variable | Métrica |
|------|----------|---------|
| **Texto de post** | Diferentes copys | Engagement (likes, comments, shares) |
| **Imagen** | Diferentes diseños | CTR, engagement |
| **Hora de publicación** | Mañana vs noche | Alcance, engagement |
| **Título de email** | Subjects diferentes | Open rate, CTR |
| **Ad copy** | Textos de anuncio | CTR, conversiones, CPA |
| **Landing page** | Diferentes versiones | Conversion rate |

### 28.3 Implementación

```python
class ABTestEngine:
    async def create_test(self, config: dict) -> dict:
        """Crea un nuevo A/B test"""
        test = {
            'id': generate_id(),
            'name': config['name'],
            'variants': config['variants'],  # [{name, content, groups}]
            'metric': config['metric'],  # engagement, clicks, conversions
            'duration_hours': config.get('duration', 48),
            'status': 'running',
            'results': {}
        }
        
        # Ejecutar ambas variantes
        for variant in test['variants']:
            for group in variant['groups']:
                await self.publish_variant(variant, group)
        
        # Programar recolección de métricas
        cron.schedule(
            f"ab_test_{test['id']}_check",
            interval="every 6 hours",
            action=lambda: self.collect_metrics(test['id'])
        )
        
        # Programar declaración de ganador
        cron.schedule(
            f"ab_test_{test['id']}_end",
            when=f"in {test['duration_hours']} hours",
            action=lambda: self.declare_winner(test['id'])
        )
        
        return test
    
    async def declare_winner(self, test_id: str):
        """Analiza resultados y declara ganador"""
        test = self.tests[test_id]
        metrics = await self.collect_metrics(test_id)
        
        winner = max(metrics, key=lambda v: v['score'])
        
        await notify(f"""
        🏆 Resultado A/B Test '{test['name']}':
        
        Variante A: {metrics[0]['score']} engagement
        Variante B: {metrics[1]['score']} engagement
        
        🎉 Ganador: {winner['name']} (+{winner['improvement']}%)
        
        ¿Escalar la variante ganadora a todos los grupos?
        """)
```

---

## 29. Sincronización entre Dispositivos

Si tienes G-Mini en múltiples PCs, pueden **sincronizar** estado y trabajar como un sistema distribuido.

### 29.1 Qué Se Sincroniza

| Dato | Método | Dirección |
|------|--------|-----------|
| **Configuración** | Cloud sync (E2E encrypted) | Bidireccional |
| **Historial de chat** | Cloud sync | Bidireccional |
| **Memoria del agente** | Cloud sync (embeddings) | Bidireccional |
| **Vault de credenciales** | Cloud sync (AES-256) | Bidireccional |
| **Skins** | Cloud sync | Bidireccional |
| **Macros/Workflows** | Cloud sync | Bidireccional |
| **Skills instaladas** | Lista sync, install local | Lista bidireccional |
| **Clipboard** | WebSocket directo P2P | Bidireccional |
| **Tareas activas** | WebSocket P2P | De origen a destino |

### 29.2 Arquitectura de Sync

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  PC Casa    │         │  Sync Server  │         │  PC Trabajo  │
│  G-Mini     │◄───────►│  (opcional)   │◄───────►│  G-Mini      │
│             │   E2E   │              │   E2E   │              │
│ ┌─────────┐ │  Encrypted│ ┌──────────┐│ Encrypted│ ┌─────────┐│
│ │ Config  │ │         │ │ Encrypted ││         │ │ Config   ││
│ │ Memory  │ │         │ │  Storage  ││         │ │ Memory   ││
│ │ Vault   │ │         │ │           ││         │ │ Vault    ││
│ └─────────┘ │         │ └──────────┘│         │ └─────────┘ │
└─────────────┘         └──────────────┘         └─────────────┘

Alternativa: P2P sin servidor (LAN o Tailscale)
```

### 29.3 Modos de Sincronización

| Modo | Descripción | Requiere Internet |
|------|-------------|-------------------|
| **Cloud Sync** | Via servidor cifrado (Firebase/Supabase) | Sí |
| **LAN Sync** | Directo entre PCs en la misma red | No |
| **Tailscale P2P** | Mesh VPN entre dispositivos | Sí (pero P2P) |
| **Manual Export/Import** | Exportar .zip → importar en otro | No |

### 29.4 Continuación de Tareas

Una tarea iniciada en PC casa puede continuar en PC trabajo:

```
[PC Casa - 17:00]
Usuario: "G-Mini, descarga y edita este video de 2GB"
G-Mini: "⬇️ Descargando... 30% completado"
→ Usuario apaga PC casa y va al trabajo

[PC Trabajo - 20:00]
G-Mini: "📌 Tienes una tarea pendiente de PC Casa:
         'Descargar y editar video' - Descarga 30%
         
         ¿Continúo la descarga aquí?"
```

### 29.5 Configuración

```yaml
sync:
  enabled: true
  mode: "cloud"  # cloud, lan, tailscale, manual
  
  cloud:
    provider: "supabase"  # o firebase
    encryption: "aes-256-gcm"
    sync_interval: 300  # cada 5 minutos
    
  lan:
    discovery: "mdns"  # mDNS para descubrir otros G-Mini en LAN
    port: 8766
    
  what_to_sync:
    config: true
    memory: true
    vault: true
    chat_history: true
    skins: true
    macros: true
    clipboard: false  # Solo bajo demanda
    
  conflict_resolution: "latest_wins"  # o manual
```

---

## 30. Sistema de Tutoriales / Onboarding

Al instalar G-Mini por primera vez, un **tutorial interactivo** guía al usuario paso a paso.

### 30.1 Flujo de Onboarding

```
┌──────────────────────────────────────────────────────┐
│  🎉 ¡Bienvenido a G-Mini Agent!                      │
│                                                       │
│  Soy tu asistente de IA personal. Puedo controlar    │
│  tu PC, automatizar tareas y mucho más.              │
│                                                       │
│  Vamos a configurarme en 5 pasos rápidos:            │
│                                                       │
│  ① Elegir proveedor de IA          [2 min]           │
│  ② Configurar tu personaje          [1 min]           │
│  ③ Primera tarea de prueba          [2 min]           │
│  ④ Conectar canales (opcional)      [3 min]           │
│  ⑤ Tour de funcionalidades          [3 min]           │
│                                                       │
│  [Empezar setup] [Saltar y configurar después]       │
└──────────────────────────────────────────────────────┘
```

### 30.2 Paso 1: Proveedor de IA

```
┌──────────────────────────────────────────────────┐
│  ① Elige tu proveedor de IA principal            │
│                                                   │
│  ☁️ Cloud (requiere API key, más potente):       │
│  ○ Claude (Anthropic) — Recomendado              │
│  ○ GPT-5 (OpenAI)                                │
│  ○ Gemini (Google)                               │
│  ○ Grok (xAI)                                    │
│  ○ DeepSeek                                      │
│                                                   │
│  🖥️ Local (gratis, sin internet):                │
│  ○ Ollama — Recomendado para local               │
│  ○ LM Studio                                     │
│  ○ vLLM                                          │
│                                                   │
│  💡 ¿No tienes API key?                          │
│  [Crear cuenta en Anthropic] [Usar Ollama gratis]│
│                                                   │
│  API Key: [____________________________]         │
│  [Probar conexión] → ✅ ¡Conectado!              │
│                                                   │
│  [← Atrás]  [Siguiente →]                       │
└──────────────────────────────────────────────────┘
```

### 30.3 Paso 2: Personaje

```
┌──────────────────────────────────────────────────┐
│  ② Configura tu personaje                         │
│                                                   │
│  ¿Cómo quieres que me vea?                       │
│                                                   │
│  Tipo: (●) 2D Sprites  ( ) 3D Modelo            │
│                                                   │
│  Skins disponibles:                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │      │ │      │ │      │ │      │           │
│  │ 😊  │ │ 🏖️  │ │ 🤖  │ │ 🎅  │           │
│  │      │ │      │ │      │ │      │           │
│  └──────┘ └──────┘ └──────┘ └──────┘           │
│  Default   Playa   Cyberpunk  Navidad           │
│                                                   │
│  Tamaño: [====●=======] 60%                     │
│  Voz: (●) Activada  ( ) Desactivada             │
│                                                   │
│  [← Atrás]  [Siguiente →]                       │
└──────────────────────────────────────────────────┘
```

### 30.4 Paso 3: Primera Tarea de Prueba

```
┌──────────────────────────────────────────────────┐
│  ③ ¡Prueba tu primer comando!                     │
│                                                   │
│  Escribe o di algo para probar. Ejemplos:        │
│                                                   │
│  💬 "¿Qué hora es?"                              │
│  📁 "Abre la carpeta Documentos"                 │
│  🌐 "Busca el clima de hoy en Google"            │
│  📝 "Crea un archivo notas.txt en el escritorio" │
│                                                   │
│  ┌──────────────────────────────────────────┐   │
│  │ Escribe tu comando aquí...        [🎤] │   │
│  └──────────────────────────────────────────┘   │
│                                                   │
│  G-Mini: "¡Hola! Soy G-Mini 🎉                  │
│  Listo para mi primera misión.                   │
│  ¿Qué quieres que haga?"                        │
│                                                   │
│  [← Atrás]  [Siguiente →]                       │
└──────────────────────────────────────────────────┘
```

### 30.5 Paso 5: Tour de Funcionalidades

El personaje **guía al usuario** mostrando las capacidades:

```python
class OnboardingTour:
    tour_steps = [
        {
            'title': 'Modos de trabajo',
            'description': 'Puedo ser programador, diseñador, pentester...',
            'demo': 'show_modes_panel',
            'character_says': 'Tengo diferentes modos. Cada uno me da superpoderes distintos.'
        },
        {
            'title': 'Control del PC',
            'description': 'Puedo ver tu pantalla y hacer clicks por ti',
            'demo': 'demo_screenshot_and_click',
            'character_says': 'Mira, puedo ver tu pantalla como la ves tú.'
        },
        {
            'title': 'Automatización',
            'description': 'Puedo repetir tareas por ti automáticamente',
            'demo': 'show_macros_panel',
            'character_says': 'Si haces algo repetitivo, grábalo y yo lo hago por ti.'
        },
        {
            'title': 'Canales',
            'description': 'Háblame por WhatsApp, Discord, Telegram...',
            'demo': 'show_gateway_config',
            'character_says': 'No tienes que estar frente a la PC. Mándame un mensaje.'
        },
        {
            'title': 'Terminales',
            'description': 'Puedo usar PowerShell, Git Bash, WSL...',
            'demo': 'show_terminal_manager',
            'character_says': 'Si eres programador, puedo usar todas tus terminales.'
        }
    ]
```

### 30.6 Tutoriales Contextuales

Además del onboarding inicial, G-Mini muestra **tips contextuales** cuando detecta que el usuario no conoce una función:

```python
class ContextualTips:
    tips = {
        'first_macro_attempt': "💡 ¿Sabías que puedo grabar eso como macro? "
                               "Di 'G-Mini graba lo que hago' la próxima vez.",
        'repeated_copy_paste': "💡 Tengo un clipboard inteligente que recuerda "
                               "todo lo que copias. Di 'G-Mini muestra mi clipboard'.",
        'manual_login': "💡 Puedo guardar esas credenciales y loguearte "
                        "automáticamente la próxima vez.",
        'long_task_no_dryrun': "💡 Para tareas largas, puedo hacer un dry run "
                                "primero. Di 'G-Mini haz un dry run de...'."
    }
```

---

## 31. Red de PCs (Multi-PC Control)

G-Mini puede controlar **múltiples PCs** como si fueran extensiones de sí mismo. Una PC tiene G-Mini como "cerebro" y las demás ejecutan un **agente ligero** que recibe y ejecuta tareas.

### 31.1 Escenario del Usuario

```
┌──────────────────────────────────────────────────────────────────┐
│                    Red de PCs del Usuario                         │
│                                                                   │
│  🖥️ PC1 "Principal"        🖥️ PC2 "Dev"         🖥️ PC3 "Media" │
│  ┌─────────────────┐     ┌────────────────┐    ┌──────────────┐ │
│  │ G-Mini Agent    │     │ G-Mini Node    │    │ G-Mini Node  │ │
│  │ (CEREBRO)       │     │ (Agente ligero)│    │ (Agente liger│ │
│  │                 │     │                │    │              │ │
│  │ IA + UI +       │────►│ Proyectos de   │    │ Videos       │ │
│  │ Personaje +     │     │ programación   │    │ grabados     │ │
│  │ control total   │◄────│ VS Code        │    │ CapCut       │ │
│  │                 │     │ Node.js        │    │ DaVinci      │ │
│  │                 │────►│ Bases de datos  │    │ After Effects│ │
│  │                 │     └────────────────┘    │ 4TB de media │ │
│  │                 │──────────────────────────►│              │ │
│  │                 │◄──────────────────────────│              │ │
│  └─────────────────┘     └────────────────┘    └──────────────┘ │
│         ▲                                                         │
│         │  WebSocket seguro (LAN o Tailscale)                    │
│         ▼                                                         │
│  📱 Celular / Tablet (Node móvil existente - Sección 9)         │
└──────────────────────────────────────────────────────────────────┘
```

### 31.2 Arquitectura: Cerebro vs Nodes PC

| Componente | PC Principal (Cerebro) | PCs Remotas (Node PC) |
|-----------|------------------------|----------------------|
| **G-Mini completo** | ✅ Sí | ❌ No |
| **Agente ligero (Node)** | — | ✅ Sí (~50MB) |
| **IA / LLM** | ✅ Procesa todas las decisiones | ❌ Solo ejecuta órdenes |
| **Personaje flotante** | ✅ Sí | ❌ Opcional (indicador de estado) |
| **Acceso a archivos** | ✅ Locales + remotos | ✅ Solo locales (expone al cerebro) |
| **Terminal** | ✅ Locales + remotas | ✅ Solo local |
| **Automatización (GUI)** | ✅ Local + remota via screenshots | ✅ Ejecuta PyAutoGUI local |
| **Captura de pantalla** | ✅ Local + solicita remotas | ✅ Captura local y envía |

### 31.3 G-Mini Node (Agente Ligero para PCs Remotas)

El Node PC es un servicio liviano que se instala en cada PC remota:

```python
# g-mini-node/main.py — Solo ~500 líneas de código
class GMiniNode:
    """Agente ligero que se instala en PCs remotas.
    No tiene IA propia — recibe órdenes del Cerebro via WebSocket."""
    
    def __init__(self, config):
        self.node_id = config['node_id']
        self.node_name = config['name']  # "PC2-Dev", "PC3-Media"
        self.cerebro_url = config['cerebro_url']  # ws://192.168.1.100:8766
        self.auth_token = config['auth_token']
        
        # Capacidades que expone
        self.capabilities = {
            'file_system': True,       # Leer, escribir, mover archivos
            'terminal': True,          # Ejecutar comandos
            'screenshot': True,        # Capturar pantalla
            'gui_automation': True,    # PyAutoGUI remoto
            'app_launcher': True,      # Abrir/cerrar apps
            'system_info': True,       # CPU, RAM, disco, procesos
            'clipboard': True,         # Leer/escribir clipboard
            'file_transfer': True,     # Enviar/recibir archivos
        }
    
    async def connect_to_cerebro(self):
        """Conecta al G-Mini principal via WebSocket"""
        async with websockets.connect(
            f"{self.cerebro_url}/node",
            extra_headers={"Authorization": f"Bearer {self.auth_token}"}
        ) as ws:
            # Registrarse
            await ws.send(json.dumps({
                'type': 'node_register',
                'node_id': self.node_id,
                'name': self.node_name,
                'capabilities': self.capabilities,
                'system_info': self.get_system_info(),
                'shared_folders': self.config.get('shared_folders', [])
            }))
            
            # Loop de comandos
            async for message in ws:
                command = json.loads(message)
                result = await self.execute_command(command)
                await ws.send(json.dumps(result))
```

### 31.4 Comandos Soportados en Nodes PC

**Archivos:**
```python
commands = {
    # === SISTEMA DE ARCHIVOS ===
    'file_list': {
        'description': 'Listar archivos en directorio remoto',
        'params': {'path': str, 'recursive': bool, 'pattern': str},
        'example': {'path': 'D:/Videos/Grabaciones', 'pattern': '*.mp4'}
    },
    'file_read': {
        'description': 'Leer contenido de archivo remoto',
        'params': {'path': str, 'encoding': str},
        'max_size': '10MB'  # Para archivos grandes, usar file_transfer
    },
    'file_write': {
        'description': 'Escribir/crear archivo en PC remota',
        'params': {'path': str, 'content': str, 'encoding': str}
    },
    'file_transfer': {
        'description': 'Transferir archivo entre PCs',
        'params': {'source_path': str, 'dest_node': str, 'dest_path': str},
        'method': 'chunked_stream',  # Streaming por chunks para archivos grandes
        'max_size': '50GB'
    },
    'file_search': {
        'description': 'Buscar archivos por nombre/contenido',
        'params': {'path': str, 'query': str, 'search_content': bool}
    },
    
    # === TERMINAL ===
    'terminal_exec': {
        'description': 'Ejecutar comando en terminal remota',
        'params': {'command': str, 'shell': str, 'cwd': str, 'timeout': int},
        'shells': ['powershell', 'cmd', 'git-bash', 'wsl']
    },
    'terminal_open': {
        'description': 'Abrir sesión de terminal persistente',
        'params': {'shell': str, 'cwd': str}
    },
    
    # === GUI REMOTO ===
    'screenshot': {
        'description': 'Capturar pantalla de PC remota',
        'params': {'monitor': int, 'region': dict},
        'returns': 'PNG base64'
    },
    'gui_click': {
        'description': 'Click en coordenadas de PC remota',
        'params': {'x': int, 'y': int, 'button': str}
    },
    'gui_type': {
        'description': 'Escribir texto en PC remota',
        'params': {'text': str, 'interval': float}
    },
    'gui_hotkey': {
        'description': 'Ejecutar atajo de teclado remoto',
        'params': {'keys': list}  # ['ctrl', 's']
    },
    
    # === APPS ===
    'app_launch': {
        'description': 'Abrir aplicación en PC remota',
        'params': {'app_name': str, 'args': list}
    },
    'app_close': {
        'description': 'Cerrar aplicación en PC remota',
        'params': {'app_name': str, 'force': bool}
    },
    'app_list': {
        'description': 'Listar aplicaciones instaladas / procesos activos',
        'params': {'type': str}  # 'installed' o 'running'
    },
    
    # === SISTEMA ===
    'system_info': {
        'description': 'Info del sistema (CPU, RAM, disco, GPU)',
        'returns': {'cpu_percent', 'ram_used', 'disk_free', 'gpu_info'}
    },
    'system_notify': {
        'description': 'Mostrar notificación en PC remota',
        'params': {'title': str, 'message': str, 'urgency': str}
    }
}
```

### 31.5 Nombrar y Registrar PCs

Cada PC tiene un nombre amigable que el usuario puede usar en comandos naturales:

```yaml
# config/network.yaml — En la PC principal (Cerebro)
network:
  role: "cerebro"  # Esta PC es el cerebro
  
  nodes:
    - id: "pc2_dev"
      name: "PC Dev"
      aliases: ["pc de programación", "pc2", "la dev", "computadora del trabajo"]
      host: "192.168.1.101"  # IP en LAN
      # o: host: "100.64.0.2"  # IP de Tailscale (si está fuera de LAN)
      port: 8766
      auth_token: "***"
      
      # Qué carpetas compartir con G-Mini
      shared_folders:
        - path: "D:/Proyectos"
          alias: "proyectos"
          description: "Todos los proyectos de programación"
        - path: "C:/Users/Dev/Desktop"
          alias: "escritorio"
      
      # Inventario de proyectos (G-Mini los descubre automáticamente)
      project_discovery:
        scan_paths: ["D:/Proyectos"]
        detect_by: ["package.json", ".git", "requirements.txt", "Cargo.toml", "*.sln"]
      
      # Apps relevantes instaladas
      apps:
        - name: "VS Code"
          path: "C:/Users/Dev/AppData/Local/Programs/Microsoft VS Code/Code.exe"
        - name: "Node.js"
          version: "22.x"
        - name: "Python"
          version: "3.12"
        - name: "Docker Desktop"
    
    - id: "pc3_media"
      name: "PC Media"
      aliases: ["pc de videos", "pc3", "la media", "computadora de edición"]
      host: "192.168.1.102"
      port: 8766
      auth_token: "***"
      
      shared_folders:
        - path: "D:/Videos/Grabaciones"
          alias: "grabaciones"
          description: "Videos grabados sin editar"
        - path: "D:/Videos/Editados"
          alias: "editados"
          description: "Videos ya editados"
        - path: "E:/Assets"
          alias: "assets"
          description: "Música, efectos, overlays"
      
      apps:
        - name: "DaVinci Resolve"
          path: "C:/Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe"
        - name: "CapCut"
        - name: "After Effects"
        - name: "Premiere Pro"
        - name: "HandBrake"
```

### 31.6 Descubrimiento Automático de Proyectos

G-Mini escanea las PCs remotas y **cataloga automáticamente** los proyectos:

```python
class ProjectDiscovery:
    """Escanea PCs remotas y cataloga proyectos"""
    
    async def scan_node(self, node_id: str) -> list:
        """Descubre proyectos en una PC remota"""
        node = self.network.get_node(node_id)
        projects = []
        
        for scan_path in node.config['project_discovery']['scan_paths']:
            # Listar todas las carpetas del path
            folders = await node.execute('file_list', {
                'path': scan_path, 
                'recursive': False
            })
            
            for folder in folders:
                project_type = await self._detect_project_type(node, folder)
                if project_type:
                    projects.append({
                        'name': folder['name'],
                        'path': folder['path'],
                        'node_id': node_id,
                        'type': project_type,  # 'nodejs', 'python', 'rust', etc.
                        'last_modified': folder['modified'],
                        'git_status': await self._get_git_status(node, folder['path']),
                        'size': folder.get('size', 0)
                    })
        
        return projects
    
    # Resultado del escaneo:
    discovered_projects = {
        'pc2_dev': [
            {'name': 'proyecto-1-api', 'type': 'nodejs', 'path': 'D:/Proyectos/proyecto-1-api'},
            {'name': 'proyecto-2-web', 'type': 'nextjs', 'path': 'D:/Proyectos/proyecto-2-web'},
            {'name': 'proyecto-3-bot', 'type': 'python', 'path': 'D:/Proyectos/proyecto-3-bot'},
            {'name': 'proyecto-4-mobile', 'type': 'flutter', 'path': 'D:/Proyectos/proyecto-4-mobile'},
            {'name': 'proyecto-5-desktop', 'type': 'electron', 'path': 'D:/Proyectos/proyecto-5-desktop'},
            {'name': 'proyecto-6-game', 'type': 'unity', 'path': 'D:/Proyectos/proyecto-6-game'},
        ],
        'pc3_media': [
            {'name': 'video_tutorial_01.mp4', 'type': 'video', 'path': 'D:/Videos/Grabaciones/...'},
            {'name': 'video_promo_marzo.mp4', 'type': 'video', 'path': 'D:/Videos/Grabaciones/...'},
            # ...
        ]
    }
```

### 31.7 Ejemplos de Uso Real

**Ejemplo 1: Editar videos de PC remota**
```
Usuario: "G-Mini, edita mis grabaciones de PC3"

G-Mini: "📡 Conectando a PC Media (PC3)...
         
         📁 Grabaciones encontradas en D:/Videos/Grabaciones:
         1. tutorial_react_01.mp4 (2.3 GB, hoy)
         2. tutorial_react_02.mp4 (1.8 GB, hoy)
         3. review_producto.mp4 (890 MB, ayer)
         4. vlog_marzo.mp4 (3.1 GB, hace 2 días)
         
         ¿Cuáles quieres editar y qué tipo de edición?"

Usuario: "Los dos tutoriales de React. Únelos, quita los silencios 
          largos y agrega intro y outro"

G-Mini: "▶️ Ejecutando en PC Media (PC3):
         
  ✅ Abriendo DaVinci Resolve en PC3...
  ✅ Importando tutorial_react_01.mp4 y tutorial_react_02.mp4
  ⏳ Detectando silencios > 2 segundos...
  ✅ 14 silencios encontrados, recortando...
  ✅ Agregando intro 'intro.mp4' de assets
  ✅ Agregando outro 'outro_suscribete.mp4' de assets
  ⏳ Exportando video final... (ETA: 8 minutos)
  
  💡 El video se exportará a D:/Videos/Editados/ en PC3.
     ¿También quieres que lo copie a esta PC?"
```

**Ejemplo 2: Corregir errores de programación en PC remota**
```
Usuario: "G-Mini, corrige errores de programación del proyecto 6 de PC2"

G-Mini: "📡 Conectando a PC Dev (PC2)...
         
         🔍 Proyecto 6 encontrado: 'proyecto-6-game' (Unity/C#)
         📂 Ubicación: D:/Proyectos/proyecto-6-game
         
         Analizando código...
         
         ⚠️ Errores encontrados:
         
         1. 📄 Assets/Scripts/PlayerController.cs:45
            NullReferenceException: 'rb' no inicializado en Start()
            
         2. 📄 Assets/Scripts/EnemyAI.cs:102
            IndexOutOfRange: Array 'waypoints' accedido sin verificar length
            
         3. 📄 Assets/Scripts/UIManager.cs:78
            Warning: Variable 'score' nunca se usa
         
         ¿Corrijo los 3 automáticamente?"

Usuario: "Sí, corrige todo"

G-Mini: "🔧 Ejecutando en PC Dev (PC2):
         
  ✅ PlayerController.cs:45 — Agregado null check + inicialización en Awake()
  ✅ EnemyAI.cs:102 — Agregado bounds check antes de acceder a waypoints[]
  ✅ UIManager.cs:78 — Conectado 'score' al texto del UI
  
  📋 Git status en PC2:
     3 archivos modificados
  
  ¿Hago commit? ¿O primero compilas en Unity para verificar?"
```

**Ejemplo 3: Tarea multi-PC simultánea**
```
Usuario: "G-Mini, mientras editas los videos en PC3, despliega 
          el proyecto 2 de PC2 a producción"

G-Mini: "🔀 Ejecutando tareas en paralelo:
         
  📹 PC3 (Media):                    🚀 PC2 (Dev):
  ├─ Abriendo DaVinci...            ├─ cd proyecto-2-web
  ├─ Importando clips...            ├─ npm run test (12/12 ✅)
  ├─ Editando silencios...          ├─ npm run build ✅
  ├─ ⏳ Exportando (45%)...         ├─ docker build ✅
  │                                  ├─ docker push ✅
  │                                  └─ ✅ Deploy completado
  └─ ⏳ Exportando (67%)...              en prod.example.com
  
  PC2 terminó. PC3 faltan ~3 minutos."
```

**Ejemplo 4: Transferir archivos entre PCs**
```
Usuario: "G-Mini, copia el video editado de PC3 a mi escritorio"

G-Mini: "📡 Transfiriendo desde PC Media (PC3):
         
  📁 D:/Videos/Editados/tutorial_react_final.mp4
  📦 Tamaño: 1.2 GB
  
  ⬇️ Copiando... ████████████░░░░ 75% (15 MB/s)
  
  ✅ Copiado a C:/Users/PC/Desktop/tutorial_react_final.mp4"
```

**Ejemplo 5: Ver estado de todas las PCs**
```
Usuario: "G-Mini, ¿cómo están mis PCs?"

G-Mini: "📊 Estado de tu red:
         
  🖥️ PC1 Principal (esta PC)     ✅ Online
     CPU: 23% | RAM: 8.2/16 GB | Disco: 234 GB libres
     
  🖥️ PC2 Dev                     ✅ Online  
     CPU: 5% | RAM: 4.1/32 GB | Disco: 890 GB libres
     Procesos: VS Code, Docker Desktop
     Proyectos: 6 detectados
     
  🖥️ PC3 Media                   ✅ Online
     CPU: 78% | RAM: 12.3/16 GB | Disco: 1.2 TB libres
     Procesos: DaVinci Resolve (exportando...)
     GPU: RTX 3060 → 92% utilización
     
  📱 Celular (Node Android)      🟡 En espera (batería 67%)"
```

### 31.8 Instalación del Node PC

La instalación del agente ligero en PCs remotas es **ultra simple**:

**Opción A — Instalación desde G-Mini (automática):**
```
Usuario: "G-Mini, agrega mi otra PC a la red"

G-Mini: "Para agregar una PC, necesito instalar un agente ligero.
         
         Opciones:
         1. [Generar instalador] → Te doy un .exe de 50MB para la otra PC
         2. [Instalar por red] → Si tengo acceso SSH/admin a la otra PC
         3. [Código de vinculación] → Escanea un QR o ingresa código
         
         ¿Cuál prefieres?"
```

**Opción B — Instalador standalone:**
```
# En la PC remota, ejecutar:
g-mini-node-setup.exe

┌──────────────────────────────────────────┐
│  G-Mini Node — Instalación               │
├──────────────────────────────────────────┤
│                                           │
│  Nombre de esta PC: [PC Dev_________]    │
│                                           │
│  Conectar a G-Mini Principal:            │
│  Código de vinculación: [A7X-9K2-M4P]   │
│                                           │
│  O escanear QR desde G-Mini Principal:   │
│  [📷 Escanear QR]                        │
│                                           │
│  Carpetas a compartir:                    │
│  ☑ D:/Proyectos                          │
│  ☑ C:/Users/Dev/Desktop                  │
│  ☐ C:/Users/Dev/Documents               │
│  [+ Agregar carpeta]                     │
│                                           │
│  [Conectar]                              │
└──────────────────────────────────────────┘
```

**Opción C — Un solo comando (avanzado):**
```powershell
# PowerShell en la PC remota:
irm https://gmini.app/node-install | iex

# O con pip:
pip install gmini-node
gmini-node setup --cerebro=192.168.1.100 --token=A7X9K2M4P
```

### 31.9 Seguridad de la Red de PCs

| Medida | Implementación |
|--------|---------------|
| **Autenticación** | Token único por node, generado en el cerebro |
| **Cifrado en tránsito** | TLS 1.3 / WSS para todo el tráfico |
| **Cifrado de archivos** | Archivos transferidos cifrados con AES-256 |
| **Autorización por carpeta** | Solo carpetas explícitamente compartidas son accesibles |
| **Aprobación de acciones** | Acciones destructivas requieren confirmación |
| **Firewall** | Solo acepta conexiones del cerebro (IP whitelist) |
| **Log de actividad** | Toda acción remota se registra en ambas PCs |
| **Desconexión remota** | El cerebro puede desconectar un node al instante |
| **Expiración de token** | Tokens expiran cada 30 días (renovación automática) |

### 31.10 Conexión Fuera de LAN (Internet)

Para controlar PCs que **no están en la misma red local**:

```yaml
# Opción 1: Tailscale (recomendado — mesh VPN gratuito)
network:
  remote_access:
    method: "tailscale"
    # Cada PC tiene Tailscale instalado
    # Se conectan automáticamente via 100.x.x.x
    nodes:
      - id: "pc2_dev"
        host: "100.64.0.2"  # IP de Tailscale
        
# Opción 2: Túnel SSH reverso
network:
  remote_access:
    method: "ssh_tunnel"
    relay_server: "relay.myserver.com"
    ssh_key: "~/.ssh/relay_key"

# Opción 3: ngrok / Cloudflare Tunnel
network:
  remote_access:
    method: "cloudflare_tunnel"
    tunnel_id: "abc123"
```

### 31.11 Configuración Completa

```yaml
# config/network.yaml
network:
  enabled: true
  role: "cerebro"  # cerebro | node
  
  # Descubrimiento automático en LAN
  auto_discovery:
    enabled: true
    method: "mdns"  # mDNS broadcast
    accept_unknown: false  # Requiere aprobación manual
  
  # Transferencia de archivos
  file_transfer:
    max_file_size: "50GB"
    chunk_size: "1MB"  
    compression: "zstd"  # Comprimir antes de transferir
    bandwidth_limit: null  # O "50MB/s" para limitar
    resume_on_disconnect: true  # Reanudar si se corta
  
  # Ejecución remota
  remote_execution:
    terminal_timeout: 300  # 5 min máximo por comando
    screenshot_quality: 80  # JPEG quality para screenshots remotos
    gui_automation_fps: 2  # Screenshots por segundo en modo GUI remoto
    
  # Acceso fuera de LAN
  remote_access:
    method: "tailscale"  # tailscale, ssh_tunnel, cloudflare, none
    fallback: "none"  # Si falla Tailscale, no intentar otra cosa
  
  # Monitoreo
  monitoring:
    health_check_interval: 30  # Ping cada 30 segundos
    alert_on_disconnect: true
    auto_reconnect: true
    auto_reconnect_interval: 60  # Reintentar cada minuto
```

---

## 32. Hogar Inteligente (Smart Home / IoT)

G-Mini puede controlar **dispositivos del hogar** — televisores, luces, alarmas, cámaras, enchufes, termostatos, cortinas, etc. — mediante comandos de voz naturales o desde el chat.

### 32.1 Escenario del Usuario

```
Usuario: "G-Mini, cambia al canal 5"
G-Mini:  "📺 Cambiando a canal 5 en la TV de la sala... ✅"

Usuario: "Apaga la luz del cuarto 4"
G-Mini:  "💡 Apagando luz del Cuarto 4... ✅"

Usuario: "Enciende la alarma de la casa"
G-Mini:  "🔔 Activando alarma perimetral... ✅ Armada en modo nocturno."

Usuario: "Pon Netflix en la TV y baja el volumen a 20"
G-Mini:  "📺 Abriendo Netflix... ✅  🔊 Volumen → 20... ✅"

Usuario: "¿Qué luces están prendidas?"
G-Mini:  "💡 Luces encendidas:
          • Sala (80%)
          • Cocina (100%)
          • Cuarto 2 (40%)
          El resto están apagadas."
```

### 32.2 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    G-Mini Agent (Cerebro)                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              SmartHomeManager                             │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  TV Bridge   │  │ Light Bridge │  │ Alarm Bridge   │  │   │
│  │  │  (LG/Samsung │  │ (Tuya/MQTT/  │  │ (Ajax/Alarm.   │  │   │
│  │  │   WebOS/     │  │  Philips Hue │  │  com/MQTT)     │  │   │
│  │  │   Tizen)     │  │  /Yeelight)  │  │                │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │   │
│  │         │                  │                   │           │   │
│  │  ┌──────┴──────┐  ┌──────┴───────┐  ┌───────┴────────┐  │   │
│  │  │ Camera      │  │ Plug Bridge  │  │ Climate Bridge │  │   │
│  │  │ Bridge      │  │ (Smart plugs │  │ (Termostato,   │  │   │
│  │  │ (ONVIF/     │  │  TP-Link/    │  │  AC, ventila-  │  │   │
│  │  │  RTSP)      │  │  Sonoff)     │  │  dores)        │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                              │                                    │
│         ┌────────────────────┼────────────────────┐              │
│         ▼                    ▼                    ▼              │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────┐        │
│  │ Home Assist. │   │   LAN Direct │   │  Cloud APIs   │        │
│  │ (hub central │   │   (WebOS TV, │   │  (Tuya Cloud, │        │
│  │  opcional)   │   │    MQTT, UPnP │   │   Alexa,     │        │
│  │  :8123       │   │    mDNS)     │   │   Google H.) │        │
│  └─────────────┘   └──────────────┘   └───────────────┘        │
│                              │                                    │
│                      Red WiFi Local                              │
└─────────────────────────────────────────────────────────────────┘
```

### 32.3 Protocolos y APIs Soportados

| Protocolo / API | Dispositivos | Librería Python | Puerto/Conexión |
|----------------|-------------|----------------|-----------------|
| **WebOS** (LG TV) | Smart TVs LG | `aiowebostv` | ws://TV_IP:3000 |
| **Tizen** (Samsung TV) | Smart TVs Samsung | `samsungtvws` | ws://TV_IP:8001 |
| **DLNA / UPnP** | TVs genéricos, media players | `async_upnp_client` | SSDP discovery |
| **Tuya** (local) | Luces, enchufes, cortinas, etc. | `tinytuya` | LAN directo (sin cloud) |
| **MQTT** | Cualquier dispositivo IoT | `asyncio-mqtt` | mqtt://broker:1883 |
| **Philips Hue** | Luces Hue, habitaciones | `aiohue` | https://bridge_ip/api |
| **Yeelight** | Luces Xiaomi/Yeelight | `yeelight` | TCP :55443 |
| **Home Assistant** | +2000 integraciones | `aiohttp` (REST API) | http://HA_IP:8123/api |
| **TP-Link Kasa** | Enchufes, luces TP-Link | `python-kasa` | LAN directo |
| **ONVIF / RTSP** | Cámaras IP | `onvif-zeep`, `cv2` | rtsp://IP:554 |
| **IR Blaster** (Broadlink) | TV, AC, cualquier control remoto | `broadlink` | LAN / IR |
| **Alexa API** | Dispositivos Alexa/Echo | `alexa-smart-home` | Cloud API |
| **Google Home** | Dispositivos Google/Nest | `glocaltokens` | Mixto (local + cloud) |

### 32.4 Control de TV (Detalle)

Las Smart TVs exponen un **servidor WebSocket** cuando se conectan al WiFi, exactamente como mencionas:

```python
class TVBridge:
    """Control de Smart TV por red local"""
    
    # === LG WebOS ===
    async def connect_lg(self, ip: str):
        """LG WebOS expone ws://IP:3000/"""
        from aiowebostv import WebOsClient
        self.client = WebOsClient(ip)
        await self.client.connect()
        # Primera vez: la TV muestra popup "¿Permitir G-Mini?"
        # Después se guarda el token y reconecta automático
    
    async def lg_commands(self):
        """Comandos disponibles para LG"""
        return {
            'channel':     self.client.set_channel,       # Cambiar canal
            'volume':      self.client.set_volume,         # Volumen (0-100)
            'mute':        self.client.set_mute,           # Silenciar
            'power_off':   self.client.power_off,          # Apagar
            'input':       self.client.set_input,          # HDMI1, HDMI2, etc.
            'app_launch':  self.client.launch_app,         # Netflix, YouTube, etc.
            'app_close':   self.client.close_app,          
            'play':        self.client.play,               # Play/Pause
            'pause':       self.client.pause,
            'media_stop':  self.client.stop,
            'screenshot':  self.client.take_screenshot,    # Captura de la TV
        }
    
    # === Samsung Tizen ===
    async def connect_samsung(self, ip: str):
        """Samsung expone ws://IP:8001/api/v2/channels/samsung.remote.control"""
        from samsungtvws import SamsungTVWS
        self.tv = SamsungTVWS(ip, name="GMiniAgent")
        self.tv.open()
    
    async def samsung_send_key(self, key: str):
        """Enviar tecla del control remoto virtual"""
        keys = {
            'power': 'KEY_POWER', 'vol_up': 'KEY_VOLUP',
            'vol_down': 'KEY_VOLDOWN', 'mute': 'KEY_MUTE',
            'ch_up': 'KEY_CHUP', 'ch_down': 'KEY_CHDOWN',
            'enter': 'KEY_ENTER', 'back': 'KEY_RETURN',
            'home': 'KEY_HOME', 'source': 'KEY_SOURCE',
            'netflix': 'KEY_NETFLIX', 'youtube': 'KEY_YOUTUBE',
            # Números para canales directos
            '0': 'KEY_0', '1': 'KEY_1', '2': 'KEY_2', 
            '3': 'KEY_3', '4': 'KEY_4', '5': 'KEY_5',
            '6': 'KEY_6', '7': 'KEY_7', '8': 'KEY_8', '9': 'KEY_9',
        }
        self.tv.send_key(keys[key])
    
    # === Genérico por Broadlink IR ===
    async def connect_ir(self, ip: str):
        """Para TVs que no tienen WiFi: usar Broadlink IR blaster"""
        import broadlink
        self.ir = broadlink.hello(ip)
        self.ir.auth()
        # Aprende los códigos IR de tu control remoto real
        # y los reproduce para cualquier dispositivo con IR
```

### 32.5 Control de Luces

```python
class LightBridge:
    """Control de luces inteligentes"""
    
    # === Tuya (marcas: Teckin, Gosund, LSC, Treatlife, etc.) ===
    async def tuya_control(self, device_id: str, action: dict):
        """Control local sin cloud — comunicación directa por LAN"""
        import tinytuya
        light = tinytuya.BulbDevice(device_id, ip, local_key)
        
        if action['type'] == 'on':
            light.turn_on()
        elif action['type'] == 'off':
            light.turn_off()
        elif action['type'] == 'brightness':
            light.set_brightness_percentage(action['value'])  # 0-100
        elif action['type'] == 'color':
            light.set_colour(action['r'], action['g'], action['b'])
        elif action['type'] == 'temperature':
            light.set_colourtemp_percentage(action['value'])  # Cálido↔Frío
    
    # === Philips Hue ===
    async def hue_control(self, room: str, action: dict):
        """Control por habitaciones/grupos"""
        from aiohue import HueBridgeV2
        bridge = HueBridgeV2(bridge_ip, app_key)
        await bridge.initialize()
        
        room_obj = bridge.groups.get_by_name(room)
        if action['type'] == 'on':
            await bridge.groups.set_state(room_obj.id, on=True)
        elif action['type'] == 'off':
            await bridge.groups.set_state(room_obj.id, on=False)
        elif action['type'] == 'scene':
            # "G-Mini, pon modo cine en la sala"
            scene = bridge.scenes.get_by_name(action['scene'])
            await bridge.scenes.recall(scene.id)
    
    # === Yeelight (Xiaomi) ===
    async def yeelight_control(self, ip: str, action: dict):
        from yeelight import Bulb
        bulb = Bulb(ip)
        match action['type']:
            case 'on':    bulb.turn_on()
            case 'off':   bulb.turn_off()
            case 'color': bulb.set_rgb(action['r'], action['g'], action['b'])
            case 'flow':  bulb.start_flow(...)  # Efectos animados
```

### 32.6 Control de Alarma y Seguridad

```python
class SecurityBridge:
    """Control de alarma y cámaras"""
    
    async def arm_alarm(self, mode: str = "away"):
        """Modos: away (fuera), home (en casa), night (noche), off"""
        # Integración depende del sistema:
        # 1. Si usa Home Assistant → REST API
        # 2. Si usa Ajax Security → Ajax Cloud API  
        # 3. Si usa alarma WiFi genérica → MQTT
        
        if self.provider == 'home_assistant':
            await self.ha_api.call_service(
                'alarm_control_panel', f'alarm_arm_{mode}',
                entity_id='alarm_control_panel.casa',
                code=self.alarm_code  # PIN cifrado del vault
            )
        elif self.provider == 'mqtt':
            await self.mqtt.publish(
                'home/alarm/set', 
                json.dumps({'state': f'ARM_{mode.upper()}'})
            )
    
    async def get_camera_snapshot(self, camera_name: str) -> bytes:
        """Captura imagen de cámara IP"""
        camera = self.cameras[camera_name]
        
        if camera['protocol'] == 'onvif':
            # ONVIF — estándar universal de cámaras IP
            snapshot_url = await self._get_onvif_snapshot_url(camera)
            async with aiohttp.ClientSession() as session:
                async with session.get(snapshot_url) as resp:
                    return await resp.read()
        
        elif camera['protocol'] == 'rtsp':
            # RTSP — capturar frame con OpenCV
            cap = cv2.VideoCapture(camera['rtsp_url'])
            ret, frame = cap.read()
            cap.release()
            return cv2.imencode('.jpg', frame)[1].tobytes()
    
    async def stream_camera(self, camera_name: str):
        """Stream en vivo de cámara al overlay de G-Mini"""
        # Muestra el feed de la cámara en una ventana flotante
        pass
```

### 32.7 Otros Dispositivos Soportados

```python
class SmartHomeBridges:
    """Bridges adicionales"""
    
    # === Enchufes inteligentes ===
    async def smart_plug(self, plug_id: str, on: bool):
        """Encender/apagar. Útil para ventiladores, calefactores, etc."""
        from kasa import SmartPlug
        plug = SmartPlug(self.devices[plug_id]['ip'])
        await plug.update()
        if on: await plug.turn_on()
        else:  await plug.turn_off()
    
    # === Termostato / AC ===
    async def climate_control(self, device: str, temp: int, mode: str):
        """Controlar AC o calefacción"""
        # Por IR Blaster (Broadlink): envía códigos infrarrojos
        # Por Tuya: muchos ACs WiFi usan Tuya
        # Por Home Assistant: soporte universal
        pass
    
    # === Cortinas motorizadas ===
    async def curtain_control(self, room: str, position: int):
        """position: 0=cerradas, 100=abiertas"""
        # Tuya, Switchbot, o MQTT
        pass
    
    # === Aspiradora robot ===
    async def vacuum_control(self, action: str):
        """start, stop, dock, spot_clean"""
        # Xiaomi Roborock: python-miio
        # Ecovacs: sucks library
        pass
    
    # === Altavoces / Audio ===
    async def speaker_control(self, speaker: str, action: dict):
        """Chromecast, Sonos, Alexa Echo"""
        # pychromecast, soco (Sonos)
        pass
```

### 32.8 Nombrar Dispositivos y Habitaciones

El usuario configura su casa con **nombres naturales**:

```yaml
# config/smart_home.yaml
smart_home:
  enabled: true
  
  # Hub central (opcional pero recomendado)
  home_assistant:
    enabled: false  # true si usa Home Assistant
    url: "http://192.168.1.50:8123"
    token: "***"  # Long-lived access token
  
  # Habitaciones de la casa
  rooms:
    - id: "sala"
      name: "Sala"
      aliases: ["living", "sala principal", "la sala"]
    - id: "cuarto_1"
      name: "Cuarto 1"
      aliases: ["mi cuarto", "habitación principal", "dormitorio"]
    - id: "cuarto_2"
      name: "Cuarto 2"
      aliases: ["cuarto de huéspedes"]
    - id: "cuarto_3"
      name: "Cuarto 3"
    - id: "cuarto_4"
      name: "Cuarto 4"
      aliases: ["cuarto del fondo"]
    - id: "cocina"
      name: "Cocina"
    - id: "garage"
      name: "Garaje"
      aliases: ["cochera", "garage"]
  
  # Dispositivos
  devices:
    # --- TVs ---
    - id: "tv_sala"
      type: "tv"
      brand: "lg"
      protocol: "webos"
      ip: "192.168.1.200"
      room: "sala"
      name: "TV de la sala"
      aliases: ["la tele", "televisor", "tv grande"]
    
    - id: "tv_cuarto1"
      type: "tv"
      brand: "samsung"
      protocol: "tizen"
      ip: "192.168.1.201"
      room: "cuarto_1"
      name: "TV del cuarto"
      aliases: ["mi tele", "tv del cuarto"]
    
    # --- Luces ---
    - id: "luz_sala"
      type: "light"
      brand: "tuya"
      protocol: "tuya_local"
      device_id: "xxx"
      local_key: "***"
      ip: "192.168.1.210"
      room: "sala"
      name: "Luz de la sala"
      capabilities: ["on_off", "brightness", "color", "temperature"]
    
    - id: "luz_cuarto4"
      type: "light"
      brand: "yeelight"
      protocol: "yeelight"
      ip: "192.168.1.214"
      room: "cuarto_4"
      name: "Luz del cuarto 4"
      capabilities: ["on_off", "brightness", "color"]
    
    - id: "luz_cocina"
      type: "light"
      brand: "philips_hue"
      protocol: "hue"
      room: "cocina"
      name: "Luz de la cocina"
      capabilities: ["on_off", "brightness", "temperature"]
    
    # --- Alarma ---
    - id: "alarma_casa"
      type: "alarm"
      brand: "generic_mqtt"
      protocol: "mqtt"
      broker: "192.168.1.50"
      topic_prefix: "home/alarm"
      name: "Alarma de la casa"
      aliases: ["la alarma", "sistema de seguridad"]
      modes: ["away", "home", "night", "off"]
      requires_pin: true  # PIN almacenado en Vault (Sección 27)
    
    # --- Cámaras ---
    - id: "camara_entrada"
      type: "camera"
      protocol: "rtsp"
      rtsp_url: "rtsp://admin:***@192.168.1.230:554/stream1"
      room: "entrada"
      name: "Cámara de la entrada"
      aliases: ["cámara de afuera", "cámara principal"]
    
    - id: "camara_garage"
      type: "camera"
      protocol: "onvif"
      ip: "192.168.1.231"
      room: "garage"
      name: "Cámara del garaje"
    
    # --- Enchufes ---
    - id: "enchufe_ventilador"
      type: "plug"
      brand: "tp-link"
      protocol: "kasa"
      ip: "192.168.1.220"
      room: "cuarto_1"
      name: "Ventilador del cuarto"
      aliases: ["el ventilador", "ventilador"]
    
    # --- IR Blaster (para dispositivos sin WiFi) ---
    - id: "ir_sala"
      type: "ir_blaster"
      brand: "broadlink"
      ip: "192.168.1.240"
      room: "sala"
      name: "Control IR de la sala"
      learned_devices:
        - name: "AC de la sala"
          aliases: ["aire acondicionado", "el aire"]
          commands: ["on", "off", "cool_24", "cool_22", "heat_26", "fan"]
        - name: "TV vieja del cuarto 3"
          commands: ["power", "vol_up", "vol_down", "ch_up", "ch_down"]
  
  # Descubrimiento automático de dispositivos
  auto_discovery:
    enabled: true
    protocols: ["upnp", "mdns", "tuya_broadcast"]
    scan_interval: 300  # Escanear cada 5 minutos
    auto_add: false  # Requiere aprobación para agregar
```

### 32.9 Procesamiento de Lenguaje Natural → Smart Home

G-Mini usa la IA para interpretar comandos ambiguos:

```python
class SmartHomeNLU:
    """Interpreta comandos naturales del usuario para el hogar"""
    
    INTENT_EXAMPLES = {
        # El LLM recibe estos ejemplos como contexto
        "cambia al canal 5": {
            "device_type": "tv", "action": "set_channel", "value": 5
        },
        "apaga la luz del cuarto 4": {
            "device_type": "light", "room": "cuarto_4", "action": "off"
        },
        "enciende la alarma": {
            "device_type": "alarm", "action": "arm", "mode": "away"
        },
        "pon Netflix en la tele": {
            "device_type": "tv", "action": "launch_app", "app": "netflix"
        },
        "baja el volumen": {
            "device_type": "tv", "action": "volume_down"
        },
        "la luz de la sala al 50%": {
            "device_type": "light", "room": "sala", 
            "action": "brightness", "value": 50
        },
        "pon la sala en modo cine": {
            "multi_action": [
                {"device_type": "light", "room": "sala", "action": "scene", "scene": "cine"},
                {"device_type": "tv", "room": "sala", "action": "power_on"}
            ]
        },
        "muéstrame la cámara de la entrada": {
            "device_type": "camera", "camera": "entrada", "action": "stream"
        },
        "¿qué temperatura hace?": {
            "device_type": "sensor", "sensor_type": "temperature", "action": "read"
        },
        "prende el ventilador y apaga la luz": {
            "multi_action": [
                {"device_type": "plug", "device": "ventilador", "action": "on"},
                {"device_type": "light", "room": "cuarto_1", "action": "off"}
            ]
        }
    }
    
    async def parse_command(self, user_text: str) -> dict:
        """Usa el LLM para interpretar el comando"""
        prompt = f"""Eres el módulo Smart Home de G-Mini Agent.
        
Dispositivos disponibles en la casa:
{json.dumps(self.device_registry, indent=2)}

Habitaciones: {', '.join(self.rooms)}

Comando del usuario: "{user_text}"

Responde SOLO con el JSON de la acción a ejecutar.
Si el usuario no especifica habitación, infiere por contexto o pregunta."""
        
        response = await self.llm.generate(prompt)
        return json.loads(response)
```

### 32.10 Escenas y Rutinas Automáticas

```yaml
# config/smart_home_scenes.yaml
scenes:
  modo_cine:
    name: "Modo Cine"
    aliases: ["modo película", "noche de pelis", "movie mode"]
    trigger: "voz"  # activar por voz
    actions:
      - device: "luz_sala"
        action: "brightness"
        value: 10  # Casi apagada
      - device: "tv_sala"
        action: "power_on"
      - device: "tv_sala"
        action: "launch_app"
        app: "netflix"
  
  buenos_dias:
    name: "Buenos Días"
    trigger: "cron"  # activar automáticamente
    schedule: "0 7 * * 1-5"  # Lunes a Viernes 7am
    actions:
      - device: "luz_cuarto1"
        action: "on"
        brightness: 30  # Suave al despertar
      - delay: 300  # 5 minutos
      - device: "luz_cuarto1"
        action: "brightness"
        value: 80  # Subir gradualmente
  
  salir_de_casa:
    name: "Salir de Casa"
    aliases: ["me voy", "ya me voy", "salgo"]
    actions:
      - device: "all_lights"
        action: "off"
      - device: "alarma_casa"
        action: "arm"
        mode: "away"
      - device: "tv_sala"
        action: "power_off"
  
  emergencia:
    name: "Emergencia"
    aliases: ["alerta", "intruso", "auxilio"]
    actions:
      - device: "all_lights"
        action: "on"
        brightness: 100
      - device: "alarma_casa"
        action: "arm"
        mode: "away"
      - notification: "⚠️ ALERTA: Modo emergencia activado"
        channels: ["push", "whatsapp"]  # Notificar al usuario
      - device: "camara_entrada"
        action: "snapshot"
        save_to: "emergencies/"
```

### 32.11 Integración con Home Assistant (Hub Universal)

Para casas con **muchos dispositivos**, Home Assistant es un hub que los unifica todos:

```python
class HomeAssistantBridge:
    """Si el usuario tiene Home Assistant, G-Mini lo usa como hub central.
    Beneficio: +2000 integraciones sin programar cada una."""
    
    def __init__(self, url: str, token: str):
        self.base_url = url  # http://192.168.1.50:8123
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def get_all_states(self) -> list:
        """Obtener estado de TODOS los dispositivos"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/states",
                headers=self.headers
            ) as resp:
                return await resp.json()
    
    async def call_service(self, domain: str, service: str, **kwargs):
        """Ejecutar cualquier acción en Home Assistant"""
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.base_url}/api/services/{domain}/{service}",
                headers=self.headers,
                json=kwargs
            )
    
    # Ejemplos de uso:
    # await ha.call_service('light', 'turn_off', entity_id='light.cuarto_4')
    # await ha.call_service('media_player', 'play_media', 
    #                        entity_id='media_player.tv_sala',
    #                        media_content_type='channel', media_content_id='5')
    # await ha.call_service('alarm_control_panel', 'alarm_arm_away',
    #                        entity_id='alarm_control_panel.casa')
```

### 32.12 Seguridad del Módulo Smart Home

| Medida | Implementación |
|--------|---------------|
| **PINs de alarma** | Almacenados en el Vault (Sección 27), nunca en texto plano |
| **Acciones peligrosas** | Desarmar alarma, abrir cerraduras → requieren confirmación por voz + PIN |
| **Comunicación local** | Preferencia por control LAN directo (sin pasar por cloud de terceros) |
| **Acceso remoto** | Si el usuario está fuera, requiere autenticación doble |
| **Logs** | Toda acción smart home se registra con timestamp y origen |
| **Modo invitado** | Visitantes solo pueden controlar luces y TV, no alarma ni cámaras |

### 32.13 Dependencias Smart Home (Python)

```
# pip install
aiowebostv>=0.4.0         # LG WebOS TV
samsungtvws>=2.6.0        # Samsung Tizen TV
tinytuya>=1.13.0          # Tuya local (luces, enchufes, etc.)
asyncio-mqtt>=0.16.0      # MQTT broker
aiohue>=4.7.0             # Philips Hue
yeelight>=0.7.0           # Xiaomi Yeelight
python-kasa>=0.7.0        # TP-Link Kasa
broadlink>=0.19.0         # IR Blaster (Broadlink)
python-miio>=0.5.0        # Xiaomi (aspiradoras, etc.)
pychromecast>=13.0.0      # Google Chromecast
async_upnp_client>=0.38.0 # UPnP/DLNA discovery
onvif-zeep>=0.2.0         # Cámaras ONVIF
zeroconf>=0.131.0         # mDNS discovery
```

---

## 33. Proveedores de IA Compatibles

### 33.1 Proveedores Cloud (requieren API key)

| Proveedor | Modelos (IDs reales de API) | SDK/API | Endpoint |
|-----------|-----------------------------|---------|----------|
| **OpenAI** | `gpt-5.2`, `gpt-5.2-pro`, `gpt-5-mini`, `gpt-5-nano`, `gpt-4.1` (opc: `gpt-5.2-codex`, `gpt-5.3-codex`) | `openai` | https://api.openai.com/v1 |
| **Anthropic** | `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` | `anthropic` | https://api.anthropic.com/v1/messages |
| **Google** | `gemini-3.1-pro-preview`, `gemini-3-flash-preview` (+ familias 3.1 Flash-Lite / 2.5 / 2.0 en Vertex) | `google-genai` | https://generativelanguage.googleapis.com/v1beta |
| **xAI** | `grok-4-1-fast-reasoning`, `grok-4-1-fast-non-reasoning`, `grok-4`, `grok-code-fast-1` (older: `grok-3`, `grok-3-mini`) | `openai` compatible / `xai-sdk` | https://api.x.ai/v1 |
| **DeepSeek** | `deepseek-chat` (V3.2), `deepseek-reasoner` (V3.2 thinking) | `openai` compatible | https://api.deepseek.com (o /v1) |

### 16.2 Proveedores Locales (sin API key, gratis)

| Runtime | Modelos Soportados | Endpoint | Protocolo |
|---------|-------------------|----------|-----------|
| **Ollama** | Qwen, Llama 3, Mistral, Mixtral, Gemma, Nemotron, GPT-OSS | `localhost:11434/v1` | OpenAI-compatible |
| **LM Studio** | Todos los modelos GGUF | `localhost:1234/v1` | OpenAI-compatible |

### 16.3 Recomendaciones por GPU

| Modelo | VRAM Requerida | Calidad |
|--------|---------------|---------|
| Qwen3-4B | 8-12 GB | Buena para tareas simples |
| GPT-OSS-20B | 16 GB | Muy buena, uso general |
| Nemotron-30B | 24-48 GB | Excelente, nivel enterprise |

### 16.4 Arquitectura del Router de Proveedores

Todos los proveedores se abstraen bajo una interfaz unificada `LLMProvider`:

```
LLMProvider (interfaz abstracta)
├── OpenAICompatibleProvider  → OpenAI, Grok, DeepSeek, Ollama, LM Studio
├── AnthropicProvider         → Claude
└── GoogleProvider            → Gemini
```

- **5 de 7 proveedores** usan API compatible con OpenAI (un solo adaptador).
- El router selecciona el proveedor según la configuración del usuario.
- Soporte para modelos **multimodales** (enviar imágenes) cuando el modelo lo permite.

---

## 34. Stack Tecnológico

### 34.1 Arquitectura General

```
┌─────────────────────────────────────────────┐
│            ELECTRON (Frontend)               │
│  ┌─────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Chat    │ │ Settings │ │  Overlay     │ │
│  │ Panel   │ │ Window   │ │  (Personaje) │ │
│  └─────────┘ └──────────┘ └──────────────┘ │
│         ↕ WebSocket / HTTP local ↕          │
├─────────────────────────────────────────────┤
│            PYTHON (Backend)                  │
│  ┌──────┐ ┌───────┐ ┌─────┐ ┌───────────┐ │
│  │Agent │ │Vision │ │Auto │ │   Voice   │ │
│  │Core  │ │(OCR+  │ │mation│ │  (Melo   │ │
│  │+LLM  │ │Omni)  │ │(PyAG)│ │   TTS)   │ │
│  └──────┘ └───────┘ └─────┘ └───────────┘ │
└─────────────────────────────────────────────┘
```

### 34.2 Frontend (Electron)

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| Framework | Electron 30+ | Ventana principal + overlay |
| UI | HTML5 + CSS3 + JavaScript/TypeScript | Interfaz moderna |
| Bundler | Vite o Webpack | Build del frontend |
| Comunicación | WebSocket (socket.io) | Bidireccional con Python |
| Overlay | BrowserWindow transparente, always-on-top | Personaje flotante |
| Animación 2D | Canvas API o PixiJS | Sprites del personaje |
| Rendering 3D | Three.js | Modelos 3D importados (.glb/.gltf) |

### 34.3 Backend (Python 3.11+)

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| Servidor | FastAPI + Uvicorn | API REST + WebSocket server |
| IA Cloud | `openai`, `anthropic`, `google-genai` SDKs | Llamadas a proveedores |
| IA Local | API compatible OpenAI | Ollama / LM Studio |
| OCR | Tesseract (`pytesseract`), EasyOCR, PaddleOCR | Extracción de texto |
| UI Understanding | OmniParser (Microsoft) | Detección de elementos UI |
| Screenshots | `mss` (10x más rápido que PyAutoGUI) | Captura de pantalla |
| Automatización | PyAutoGUI + pynput | Clicks, teclado, mouse |
| ADB | `pure-python-adb` o subprocess `adb` | Control de Android |
| TTS | MeloTTS | Síntesis de voz offline |
| Audio | `sounddevice` o `pygame.mixer` | Reproducción de audio |
| ML Runtime | PyTorch (incluido completo) | Inferencia de modelos |

### 34.4 Empaquetado

| Aspecto | Decisión |
|---------|----------|
| Python → exe | PyInstaller `--onedir` (no `--onefile`) |
| Electron → exe | electron-builder |
| Instalador | NSIS o Inno Setup (combina Electron + Python) |
| Tamaño estimado | ~3-6 GB (con PyTorch GPU + todos los modelos) |
| Modelos ML | Incluidos en la instalación |
| Distribución | Instalador .exe descargable |

---

## 35. Sistema de Visión

### 35.1 Modos de Visión (Configurable por el usuario)

El sistema ofrece **2 modos de operación** que el usuario puede seleccionar desde la configuración:

---

#### Modo 1 — Computer Use (Imagen directa)

Comportamiento clásico tipo "computer use". Envía la captura de pantalla completa al modelo de IA.

```
Captura de pantalla (mss)
    │
    └─→ Imagen completa (base64) → Se envía directo al LLM multimodal
                                    │
                                    └─→ La IA analiza visualmente y decide qué hacer
                                         (click, escribir, scroll, etc.)
```

| Aspecto | Detalle |
|---------|---------|
| Ventaja | Máxima precisión visual, la IA "ve" todo |
| Desventaja | Alto consumo de tokens (~2000-5000 por captura) |
| Requiere | Modelo multimodal (GPT-4o, Claude 3.5, Gemini Pro, etc.) |
| Ideal para | Tareas complejas, UIs desconocidas, debugging visual |

---

#### Modo 2 — Token Saver (Solo texto, imagen solo si hay error)

Modo inteligente que ahorra tokens. **No envía imágenes** al modelo a menos que ocurra un error. Solo envía texto estructurado (OCR + elementos UI detectados) y la IA decide qué hacer basándose en texto.

```
Captura de pantalla (mss)
    │
    ├─→ OmniParser → Detecta elementos UI (botones, campos, links)
    │     Salida: lista de {bbox, label, tipo, id}
    │
    └─→ Motor OCR (configurable) → Extrae todo el texto visible
          Salida: lista de {texto, bbox, confianza}
    
    Ambas salidas se combinan en texto estructurado
    │
    └─→ Se envía SOLO TEXTO al LLM
        │
        └─→ La IA responde con la acción:
             "click en elemento id:7 (botón Guardar)"
             "escribir 'hola' en campo id:3 (input Email)"
    
    ¿La acción falló o hubo error?
    │
    ├─→ NO: Continúa en modo texto (siguiente captura)
    │
    └─→ SÍ: Escala a Modo 1 temporalmente
              → Envía captura como imagen al LLM
              → La IA diagnostica visualmente el problema
              → Resuelve y vuelve a Modo 2
```

| Aspecto | Detalle |
|---------|---------|
| Ventaja | ~80-90% menos tokens, funciona con modelos solo-texto |
| Desventaja | Puede fallar en UIs muy visuales o no estándar |
| Requiere | Cualquier modelo (no necesita ser multimodal) |
| Ideal para | Tareas repetitivas, formularios, navegación web estándar |
| Fallback | Si hay error → escala a imagen temporalmente |

---

#### Comparación de modos

| Característica | Modo 1 (Computer Use) | Modo 2 (Token Saver) |
|---------------|----------------------|----------------------|
| Envía imagen | Siempre | Solo si hay error |
| Tokens por paso | ~2000-5000 | ~200-1000 |
| Modelo requerido | Multimodal | Cualquiera |
| Precisión | Muy alta | Alta (con fallback) |
| Costo API | Alto | Bajo |
| Velocidad | Más lento (procesar imagen) | Más rápido (solo texto) |

El usuario puede cambiar de modo en cualquier momento desde la configuración, o el agente puede sugerir cambiar si detecta muchos errores en Modo 2.

### 35.2 Pipeline Detallado del Modo 2 (Token Saver)

**Formato de salida enviado al LLM (ejemplo):**

```
=== PANTALLA ACTUAL ===

[ELEMENTOS UI DETECTADOS] (OmniParser)
  id:1  | tipo: botón    | label: "Archivo"      | pos: (12, 5)
  id:2  | tipo: botón    | label: "Editar"        | pos: (80, 5)
  id:3  | tipo: input    | label: "Buscar..."     | pos: (300, 5)
  id:4  | tipo: checkbox | label: "Recordarme"    | pos: (200, 300) | estado: unchecked
  id:5  | tipo: botón    | label: "Iniciar sesión"| pos: (200, 350)
  id:6  | tipo: link     | label: "Olvidé mi contraseña" | pos: (200, 380)

[TEXTO VISIBLE] (OCR)
  "Bienvenido a la aplicación"  pos: (150, 100)
  "Usuario:"                     pos: (100, 200)
  "admin@example.com"              pos: (200, 230)
  "Contraseña:"                  pos: (100, 270)

=== FIN PANTALLA ===

Tarea: Iniciar sesión con las credenciales ya escritas.
¿Qué acción realizar?
```

**Respuesta esperada del LLM:**
```json
{"action": "click", "target": "id:5", "reason": "Click en botón Iniciar sesión"}
```

### 35.3 Optimización de Tokens (dentro de cada modo)

| Modo | Escenario | Qué envía | Tokens aprox. |
|------|-----------|----------|---------------|
| Modo 1 | Siempre | Imagen completa (base64) | ~2000-5000 |
| Modo 2 | Flujo normal | Solo texto OCR + UI elements | ~200-1000 |
| Modo 2 | Error detectado | Imagen completa + texto (fallback) | ~2000-5000 |
| Modo 2 | Error resuelto | Vuelve a solo texto | ~200-1000 |

### 35.4 Motores OCR Disponibles

| Motor | Peso | Velocidad | Precisión texto pantalla | Idiomas |
|-------|------|-----------|-------------------------|---------|
| **Tesseract** | ~60 MB | Rápido | Buena | 100+ |
| **EasyOCR** | ~200 MB (+PyTorch) | Medio | Muy buena | 80+ |
| **PaddleOCR** | ~500 MB (+Paddle) | Rápido | Excelente | 80+ |

El usuario elige cuál usar desde la configuración. Los tres se incluyen.

---

## 36. Sistema de Automatización

### 36.1 Acciones de Escritorio

| Acción | Librería | Función |
|--------|---------|---------|
| Click en coordenada | PyAutoGUI | `pyautogui.click(x, y)` |
| Click en elemento detectado | OmniParser + PyAutoGUI | Detectar bbox → calcular centro → click |
| Escribir texto | PyAutoGUI | `pyautogui.write(text)` / `typewrite()` |
| Hotkeys | PyAutoGUI | `pyautogui.hotkey('ctrl', 'c')` |
| Scroll | PyAutoGUI | `pyautogui.scroll(clicks)` |
| Drag & drop | PyAutoGUI | `pyautogui.moveTo()` + `drag()` |
| Escuchar teclas | pynput | Listener en background |
| Screenshot | mss | `sct.grab(monitor)` |

### 36.2 Acciones en Android (ADB)

| Acción | Comando ADB |
|--------|-------------|
| Tap | `adb shell input tap x y` |
| Swipe | `adb shell input swipe x1 y1 x2 y2` |
| Escribir | `adb shell input text "texto"` |
| Screenshot | `adb exec-out screencap -p > screen.png` |
| Abrir app | `adb shell am start -n paquete/actividad` |
| Botón back | `adb shell input keyevent 4` |

### 36.3 Flujo del Agente (Loop Principal)

```
INICIO
  │
  ▼
[1] Capturar pantalla (mss)
  │
  ▼
[2] Analizar (OCR + OmniParser)
  │
  ▼
[3] Construir prompt con contexto:
    - Historial de conversación
    - Resultado OCR / UI elements
    - Imagen (si es necesario)
    - Instrucciones del sistema
    - Herramientas disponibles (function calling)
  │
  ▼
[4] Enviar al LLM seleccionado
  │
  ▼
[5] LLM responde con:
    ├── Texto → Mostrar en chat + TTS
    ├── Acción → Ejecutar (click, escribir, etc.)
    └── Pregunta → Solicitar input al usuario
  │
  ▼
[6] Si acción ejecutada → volver a [1] (verificar resultado)
    Si tarea completada → Notificar al usuario
    Si error → Reintentar o pedir ayuda
  │
  ▼
FIN (cuando el usuario detiene o la tarea se completa)
```

---

## 37. Asistente Virtual (Personaje Flotante)

El personaje es una ventana **transparente, sin bordes, siempre visible** sobre el escritorio.
Flota sobre todo el contenido como un asistente virtual visible en todo momento.

**Referencia visual (capturas del concepto):**
```
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
│  Escritorio del usuario (iconos, apps, etc.)                    │
│                                                                  │
│                         ┌──────────┐                             │
│                         │ [─] [✕]  │ ← Solo visible al hover    │
│                         │          │                             │
│                         │  ╔════╗  │                             │
│                         │  ║    ║  │                             │
│                         │  ║ 2D ║  │  Personaje transparente     │
│                         │  ║ /  ║  │  sin fondo, sobre el        │
│                         │  ║ 3D ║  │  escritorio                 │
│                         │  ║    ║  │                             │
│                         │  ╚════╝  │                             │
│                         │          │                             │
│                         └──────────┘                             │
│                                                                  │
│  ┌─────────┐                                                     │
│  │ 🔍Buscar│                                    11:03  ESP      │
│  └─────────┘                                                     │
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

### 37.1 Ventana del Overlay — Comportamiento

| Propiedad | Comportamiento |
|-----------|---------------|
| Fondo | **100% transparente** — solo se ve el personaje, sin rectángulo ni borde |
| Siempre encima | Sí (`alwaysOnTop: true`) — visible sobre todas las apps |
| Barra de título | **No tiene** — ventana sin marco (`frame: false`) |
| Botones ─ y ✕ | **Solo aparecen al acercar el cursor** (hover). Desaparecen al alejar el mouse |
| Minimizar (─) | Oculta el personaje al system tray. Click en tray lo restaura |
| Cerrar (✕) | Oculta el personaje (no cierra la app). Se reactiva desde tray o settings |
| Redimensionar | **Scroll del mouse sobre el personaje** para agrandar/achicar. También desde configuración (slider de tamaño) |
| Mover | **Drag & drop** — click y arrastrar el personaje a cualquier parte de la pantalla |
| Click-through | Durante automatización del agente: `pointer-events: none` para no interferir con clicks de PyAutoGUI |
| Taskbar | **No aparece** en la barra de tareas (window type: `'toolbar'`) |
| Multi-monitor | Se puede arrastrar a cualquier monitor |

**Implementación de botones hover en Electron:**
```
Cursor fuera del overlay:
  → Botones ocultos (opacity: 0)
  → Solo se ve el personaje

Cursor entra al overlay:
  → Botones [─] [✕] aparecen con fade-in (opacity: 1, transition: 0.2s)
  → Posición: esquina superior derecha del personaje
  → Fondo semi-transparente para que se lean sobre el personaje

Cursor sale del overlay:
  → Botones desaparecen con fade-out (opacity: 0, transition: 0.3s)
```

### 37.2 Modo 2D (Sprites)

**Imágenes requeridas del usuario (PNG con transparencia):**
1. `idle.png` — Boca cerrada, ojos abiertos (estado por defecto)
2. `talk.png` — Boca abierta, ojos abiertos
3. `blink.png` — Boca cerrada, ojos cerrados
4. `blink_talk.png` — Boca abierta, ojos cerrados

**Ejemplo visual de estados:**
```
  idle.png       talk.png      blink.png    blink_talk.png
  ┌──────┐       ┌──────┐      ┌──────┐      ┌──────┐
  │ o  o │       │ o  o │      │ ─  ─ │      │ ─  ─ │
  │  __  │       │  ()  │      │  __  │      │  ()  │
  │      │       │      │      │      │      │      │
  └──────┘       └──────┘      └──────┘      └──────┘
  ojos:abiertos  ojos:abiertos ojos:cerrados ojos:cerrados
  boca:cerrada   boca:abierta  boca:cerrada  boca:abierta
```

**Lógica de animación:**
- **Idle**: Muestra `idle.png`. Cada 3-5 segundos (aleatorio), parpadea mostrando `blink.png` por 150ms.
- **Hablando**: Alterna entre `idle.png` y `talk.png` sincronizado con la energía (RMS) del audio TTS o del stream de voz real-time.
  - Si RMS > threshold → `talk.png` (boca abierta)
  - Si RMS ≤ threshold → `idle.png` (boca cerrada)
- **Hablando + Parpadeo**: Combina ambas lógicas, usando `blink_talk.png` cuando coinciden.

**Reacciona al hablar:**
- En **Modo Texto + TTS**: Se anima con el audio generado por MeloTTS
- En **Modo STT (🎤)**: Se anima cuando el agente responde con TTS
- En **Modo Voz Real-Time (📞)**: Se anima en tiempo real con el audio de respuesta del proveedor

**Implementación en Electron:**
- BrowserWindow separada: `transparent: true`, `frame: false`, `alwaysOnTop: true`
- Canvas o PixiJS para renderizar sprites con alpha channel
- Fondo del canvas: `transparent` (el usuario solo ve el personaje)
- CSS: `pointer-events: none` durante automatización del agente
- Draggable por el usuario cuando está en modo interactivo
- Resize con scroll wheel: `wheel` event → escalar el sprite proporcionalmente

### 37.3 Modo 3D (Modelo Importado)

**Formatos soportados:** `.glb`, `.gltf` (estándar web 3D)

El usuario puede importar su propio modelo 3D desde la configuración. El modelo se renderiza en una ventana transparente con Three.js.

**Implementación:**
- **Three.js** en la ventana overlay de Electron con fondo transparente (`alpha: true`)
- El renderer usa `setClearColor(0x000000, 0)` para fondo 100% transparente
- El usuario importa el modelo 3D desde el panel de configuración (drag & drop o file picker)
- El modelo se guarda en `assets/characters/custom/`

**Animaciones del modelo 3D:**
- **Idle**: Respiración suave (translate Y sube/baja) + balanceo leve
- **Hablando**: Si el modelo tiene **morph targets** para boca → lipsync con RMS del audio. Si no tiene morph targets → vibración sutil del modelo + efecto glow
- **Parpadeo**: Si el modelo tiene morph targets para ojos → parpadeo cada 3-5s. Si no → skip
- **Fallback**: Si el modelo no tiene animaciones ni morph targets → rotación suave como idle

**Redimensionar:**
- Scroll del mouse sobre el modelo → escala el modelo (Three.js `camera.zoom` o `object.scale`)
- También configurable con slider en settings
- Tamaño mínimo y máximo configurable

### 37.4 Importar Personaje (Configuración)

Desde el panel de **Settings → Personaje**:

```
┌─────────────────────────────────────────────┐
│  Configuración de Personaje                  │
├─────────────────────────────────────────────┤
│                                              │
│  Tipo: (●) 2D Sprites  ( ) 3D Modelo       │
│                                              │
│  ── 2D Sprites ──────────────────────────── │
│  idle.png:       [idle.png ✓]    [Cambiar]  │
│  talk.png:       [talk.png ✓]    [Cambiar]  │
│  blink.png:      [blink.png ✓]   [Cambiar]  │
│  blink_talk.png: [blink_talk ✓]  [Cambiar]  │
│                                              │
│  ── 3D Modelo ───────────────────────────── │
│  Archivo:  [modelo.glb]   [Importar .glb]   │
│                                              │
│  ── Apariencia ──────────────────────────── │
│  Tamaño:   [====●=======] 60%               │
│  Opacidad: [========●===] 85%               │
│  Posición: [Esquina inferior derecha ▼]      │
│                                              │
│  [Vista previa]    [Restaurar default]       │
└─────────────────────────────────────────────┘
```

### 37.5 Sistema de Skins (Presets de Apariencia)

G-Mini puede tener **múltiples apariencias/estilos** llamados **skins** o **presets**. El usuario puede cambiar entre ellos con comandos de voz o texto.

**Estructura de una Skin:**
```yaml
# config/skins/estilo_playa.yaml
skin:
  id: "estilo_playa"
  name: "Estilo de Playa"
  aliases: ["playa", "verano", "beach"]
  description: "Look veraniego con sombrero de paja y lentes de sol"
  
  # Assets según tipo
  type: "2d"  # o "3d"
  
  # Para 2D:
  sprites:
    idle: "skins/playa/idle.png"
    talk: "skins/playa/talk.png"
    blink: "skins/playa/blink.png"
    blink_talk: "skins/playa/blink_talk.png"
  
  # Para 3D:
  # model: "skins/playa/modelo_playa.glb"
  
  # Ajustes opcionales
  settings:
    default_size: 70
    default_opacity: 100
    glow_color: "#FFD700"  # Dorado playero
```

**Cambiar de Skin por Comando:**

| Comando del Usuario | Acción |
|---------------------|--------|
| "G-Mini cámbiate a estilo de playa" | Cambia a skin `estilo_playa` |
| "G-Mini usa el preset navideño" | Cambia a skin `navidad` |
| "G-Mini vuelve al estilo normal" | Cambia a skin `default` |
| "G-Mini cámbiate de preset1 a preset2" | Cambia de skin actual a `preset2` |
| "G-Mini muéstrame tus skins disponibles" | Lista todas las skins instaladas |
| "G-Mini ¿qué skin tienes ahora?" | Dice el nombre de la skin actual |

**Ejemplos de Skins Predefinidas:**
```
📁 assets/skins/
├── 📁 default/           # Apariencia base
│   ├── idle.png
│   ├── talk.png
│   ├── blink.png
│   └── blink_talk.png
├── 📁 estilo_playa/      # Look veraniego
│   ├── idle.png          # Con sombrero y lentes de sol
│   ├── talk.png
│   ├── blink.png
│   └── blink_talk.png
├── 📁 navidad/           # Temática navideña
│   ├── idle.png          # Con gorro de Santa
│   └── ...
├── 📁 halloween/         # Temática Halloween
│   ├── modelo.glb        # Modelo 3D con disfraz
│   └── skin.yaml
├── 📁 cyberpunk/         # Estilo futurista
│   └── ...
└── 📁 profesional/       # Look formal/oficina
    └── ...
```

**Implementación del Cambio de Skin:**
```python
class SkinManager:
    def __init__(self):
        self.skins = {}
        self.current_skin = "default"
        self.load_all_skins()
    
    def load_all_skins(self):
        """Carga todas las skins de assets/skins/"""
        skins_dir = Path("assets/skins")
        for skin_folder in skins_dir.iterdir():
            if skin_folder.is_dir():
                config = skin_folder / "skin.yaml"
                if config.exists():
                    skin_data = yaml.safe_load(config.read_text())
                    self.skins[skin_data['skin']['id']] = skin_data['skin']
                else:
                    # Auto-detectar skin 2D si hay sprites
                    self._auto_detect_skin(skin_folder)
    
    def change_skin(self, skin_identifier: str) -> dict:
        """Cambia a una skin por ID o alias"""
        # Buscar por ID exacto
        if skin_identifier in self.skins:
            return self._apply_skin(skin_identifier)
        
        # Buscar por alias (fuzzy match)
        for skin_id, skin_data in self.skins.items():
            aliases = skin_data.get('aliases', [])
            if skin_identifier.lower() in [a.lower() for a in aliases]:
                return self._apply_skin(skin_id)
            # Match parcial en nombre
            if skin_identifier.lower() in skin_data['name'].lower():
                return self._apply_skin(skin_id)
        
        return {"error": f"Skin '{skin_identifier}' no encontrada"}
    
    def _apply_skin(self, skin_id: str) -> dict:
        """Aplica la skin y notifica al frontend"""
        self.current_skin = skin_id
        skin_data = self.skins[skin_id]
        
        # Emitir evento al frontend para cambiar assets
        socketio.emit('skin_changed', {
            'skin_id': skin_id,
            'skin_data': skin_data
        })
        
        return {
            "success": True,
            "message": f"¡Listo! Ahora tengo el estilo '{skin_data['name']}' 🎨",
            "skin": skin_data
        }
    
    def list_skins(self) -> list:
        """Lista todas las skins disponibles"""
        return [
            {
                'id': s['id'],
                'name': s['name'],
                'description': s.get('description', ''),
                'is_current': s['id'] == self.current_skin
            }
            for s in self.skins.values()
        ]
```

**Configuración en Settings → Personaje → Skins:**
```
┌─────────────────────────────────────────────┐
│  Skins Disponibles                           │
├─────────────────────────────────────────────┤
│                                              │
│  ● Default            [Vista previa]         │
│    Apariencia base de G-Mini                 │
│                                              │
│  ○ Estilo de Playa    [Vista previa]         │
│    Look veraniego con sombrero y lentes      │
│                                              │
│  ○ Navidad            [Vista previa]         │
│    Temática navideña con gorro de Santa      │
│                                              │
│  ○ Cyberpunk          [Vista previa]         │
│    Estilo futurista con neones               │
│                                              │
│  ─────────────────────────────────────────── │
│  [+ Importar Skin]  [📁 Abrir carpeta skins] │
│                                              │
│  Skin actual: Default                        │
│  [Aplicar selección]                         │
└─────────────────────────────────────────────┘
```

**Importar Nuevas Skins:**
1. **Manual**: Arrastrar carpeta con sprites/modelo a `assets/skins/`
2. **Desde UI**: Botón "Importar Skin" → seleccionar carpeta o .zip
3. **Marketplace** (futuro): Descargar skins de la comunidad

**Comandos del Agente para Skins:**
```python
# El agente tiene acceso a estas herramientas:
tools = [
    {
        "name": "change_skin",
        "description": "Cambia la apariencia/skin del personaje de G-Mini",
        "parameters": {
            "skin_name": "Nombre o alias de la skin a aplicar"
        }
    },
    {
        "name": "list_skins", 
        "description": "Lista todas las skins disponibles"
    },
    {
        "name": "get_current_skin",
        "description": "Obtiene la skin actual del personaje"
    }
]
```

---

## 38. Interfaz de Usuario (Electron)

### 38.1 Ventanas

| Ventana | Tipo | Descripción |
|---------|------|-------------|
| **Principal** | Normal | Chat + controles del agente |
| **Overlay** | Transparente, sin marco | Personaje animado flotante |
| **Settings** | Modal/Tab | Configuración completa |
| **Tray** | System tray | Acceso rápido, minimizar a tray |

### 38.2 Panel de Chat (Ventana Principal)

```
┌─────────────────────────────────────────────┐
│ G-Mini Agent          [Modelo: GPT-5.2 ▼]  │
├─────────────────────────────────────────────┤
│                                             │
│  🤖 Agente: ¡Hola! ¿En qué te ayudo?      │
│                                             │
│  👤 Tú: Abre Chrome y busca el clima       │
│                                             │
│  🤖 Agente: Abriendo Chrome...             │
│  [📷 Preview: screenshot del agente]        │
│  🤖 Agente: Listo, el clima es 22°C ☀️     │
│                                             │
├─────────────────────────────────────────────┤
│ ┌─────────────────────────┐ 🎤  📞  ⏸️ ⏹️ │
│ │ Escribe un mensaje...   │                 │
│ └─────────────────────────┘                 │
└─────────────────────────────────────────────┘
```

**Elementos del panel:**
- Historial de mensajes (usuario ↔ agente) con scroll
- Input de texto (⌨️) — siempre disponible
- **Botón 🎤 (Micrófono)** — Speech-to-Text, convierte voz a texto y lo pone en el input
- **Botón 📞 (Teléfono)** — Conversación de voz real-time (se deshabilita si el modelo no lo soporta)
- **Botón ⏸️ (Pausa)** — Pausa al agente
- **Botón ⏹️ (Stop)** — Detiene al agente completamente
- Indicador de estado del agente (💭 pensando, 🔧 actuando, 😴 idle, 🎙️ escuchando, 📞 en llamada)
- Preview de lo que el agente "ve" (thumbnail de screenshot + elementos detectados)
- Selector de modelo activo (dropdown arriba)

### 38.3 Panel de Configuración

**Tabs:**

1. **General**: Idioma de la app, tema (dark/light), inicio con Windows, minimizar a tray
2. **Modelo de IA**: Selector de proveedor, API keys, modelo específico, temperatura, max tokens
3. **Visión**: Motor OCR a usar, modo de visión (Computer Use / Token Saver), sensibilidad de OmniParser, frecuencia de captura, resolución
4. **Automatización**: Velocidad de acciones, confirmación antes de actuar, áreas permitidas/bloqueadas de pantalla
5. **Personaje**: Modo 2D/3D, importar sprites/modelo, tamaño, posición default, opacidad
6. **Voz y Micrófono**: Activar TTS, idioma MeloTTS, speaker, velocidad, volumen, motor STT (Whisper/Web Speech API), dispositivo de micrófono, hotkey push-to-talk
7. **Voz Real-Time**: Configurar API real-time de OpenAI/Gemini/Grok, voz preferida del proveedor, calidad de audio
8. **ADB**: Configuración del dispositivo Android, IP/puerto, activar/desactivar
9. **Modelos locales**: Configurar Ollama endpoint, LM Studio endpoint, estado de conexión
10. **Avanzado**: Logs, debug mode, proxy, GPU selection

---

## 39. Estructura del Proyecto

```
G-Mini-Agent/
│
├── electron/                           # Frontend Electron
│   ├── package.json
│   ├── main.js                         # Proceso principal Electron
│   ├── preload.js                      # Preload scripts
│   ├── src/
│   │   ├── index.html                  # Ventana principal
│   │   ├── overlay.html                # Ventana del personaje
│   │   ├── css/
│   │   │   ├── main.css
│   │   │   ├── overlay.css
│   │   │   └── themes/
│   │   ├── js/
│   │   │   ├── app.js                  # Lógica principal UI
│   │   │   ├── chat.js                 # Panel de chat
│   │   │   ├── settings.js             # Panel de configuración
│   │   │   ├── character2d.js          # Animador de sprites 2D (PixiJS/Canvas)
│   │   │   ├── character3d.js          # Renderer 3D (Three.js)
│   │   │   ├── overlay-controls.js     # Botones hover (minimizar/cerrar) + resize + drag
│   │   │   ├── websocket.js            # Comunicación con Python backend
│   │   │   └── tray.js                 # System tray
│   │   └── assets/
│   │       ├── icons/
│   │       └── default-character/      # Sprites por defecto
│   └── electron-builder.yml            # Config de empaquetado
│
├── backend/                            # Backend Python
│   ├── main.py                         # Entry point (FastAPI + Uvicorn)
│   ├── config.py                       # Gestión de configuración (YAML)
│   ├── requirements.txt
│   │
│   ├── core/
│   │   ├── agent.py                    # Loop principal del agente
│   │   ├── planner.py                  # Planificación de tareas multi-paso
│   │   ├── memory.py                   # Historial de conversación + contexto
│   │   └── token_manager.py            # Conteo y optimización de tokens
│   │
│   ├── providers/
│   │   ├── base.py                     # Clase abstracta LLMProvider
│   │   ├── openai_compat.py            # OpenAI, Grok, DeepSeek, Ollama, LM Studio
│   │   ├── anthropic_provider.py       # Claude (Anthropic)
│   │   ├── google_provider.py          # Gemini (Google)
│   │   └── router.py                   # Selector de proveedor
│   │
│   ├── vision/
│   │   ├── screen_capture.py           # Screenshots (mss)
│   │   ├── ocr_engine.py              # Abstracción OCR (Tesseract/EasyOCR/PaddleOCR)
│   │   ├── ui_parser.py               # OmniParser integration
│   │   └── token_optimizer.py          # Decide qué enviar al LLM (texto vs imagen)
│   │
│   ├── automation/
│   │   ├── desktop.py                  # PyAutoGUI + pynput wrapper
│   │   ├── adb_controller.py           # Control Android via ADB
│   │   └── actions.py                  # Acciones de alto nivel
│   │
│   ├── voice/
│   │   ├── tts_engine.py              # MeloTTS wrapper
│   │   ├── stt_engine.py              # Speech-to-Text (Whisper / Web Speech API)
│   │   ├── realtime_voice.py          # Voz real-time (OpenAI/Gemini/Grok WebSocket)
│   │   ├── audio_player.py            # Reproducción de audio
│   │   └── lipsync.py                 # Análisis RMS → estados de boca
│   │
│   ├── api/
│   │   ├── routes.py                   # Endpoints REST
│   │   ├── websocket_handler.py        # WebSocket handler
│   │   └── schemas.py                  # Pydantic models
│   │
│   └── utils/
│       ├── logger.py                   # Logging
│       ├── dpi_utils.py                # Manejo de DPI scaling
│       └── gpu_utils.py                # Detección de GPU
│
├── models/                             # Modelos ML (incluidos en instalación)
│   ├── ocr/
│   ├── omniparser/
│   └── melotts/
│
├── assets/
│   ├── characters/
│   │   └── default/                    # Personaje 2D por defecto
│   │       ├── idle.png
│   │       ├── talk.png
│   │       ├── blink.png
│   │       └── blink_talk.png
│   └── sounds/
│
├── scripts/
│   ├── build.py                        # Script de build completo
│   ├── build_electron.py               # Build del frontend
│   ├── build_python.py                 # Build del backend (PyInstaller)
│   └── create_installer.nsi            # Script NSIS para instalador
│
├── config.default.yaml                 # Configuración por defecto
├── README.md
└── LICENSE
```

---

## 40. Comunicación Electron ↔ Python

### 40.1 Protocolo

| Canal | Tecnología | Uso |
|-------|-----------|-----|
| **WebSocket** | socket.io (Python: `python-socketio`, JS: `socket.io-client`) | Eventos en tiempo real (chat, estado, lipsync) |
| **HTTP REST** | FastAPI | Configuración, CRUD, operaciones one-shot |

### 40.2 Eventos WebSocket

| Evento | Dirección | Payload |
|--------|-----------|---------|
| `agent:message` | Python → Electron | `{text, type, timestamp}` |
| `agent:status` | Python → Electron | `{status: "thinking"\|"acting"\|"idle"\|"listening"\|"calling"}` |
| `agent:screenshot` | Python → Electron | `{image_b64, elements, ocr_text}` |
| `agent:lipsync` | Python → Electron | `{state: "idle"\|"talk"\|"blink"\|"blink_talk"}` |
| `agent:audio` | Python → Electron | `{audio_b64, duration}` |
| `user:message` | Electron → Python | `{text, attachments}` |
| `user:command` | Electron → Python | `{action: "start"\|"stop"\|"pause"\|"voice_start"\|"voice_stop"}` |
| `user:config` | Electron → Python | `{section, key, value}` |
| `user:stt_audio` | Electron → Python | `{audio_b64, format}` (audio grabado para STT) |
| `user:realtime_audio` | Electron → Python | `{audio_chunk_b64}` (stream de micrófono para voz RT) |
| `agent:realtime_audio` | Python → Electron | `{audio_chunk_b64}` (stream de respuesta voz RT) |
| `agent:stt_result` | Python → Electron | `{text, confidence}` (resultado de transcripción) |

---

## 41. Manejo de DPI y Multi-Monitor

| Problema | Solución |
|----------|----------|
| Coordenadas desfasadas en HiDPI | `ctypes.windll.shcore.SetProcessDpiAwareness(2)` al inicio |
| Multi-monitor con diferentes DPI | `mss` reporta coordenadas absolutas; mapear a monitor correcto |
| Overlay en monitor incorrecto | Electron permite especificar `BrowserWindow.setBounds()` por display |

---

## 42. Seguridad y Sandboxing

### 42.1 Medidas de Seguridad Base

| Aspecto | Medida |
|---------|--------|
| API Keys | Almacenadas encriptadas localmente (keyring o AES) |
| Automatización | Opción de confirmar antes de ejecutar acciones destructivas |
| Zonas prohibidas | El usuario puede definir áreas de pantalla donde el agente NO puede hacer click |
| Kill switch | Hotkey global (ej: Ctrl+Shift+Esc) para detener inmediatamente al agente |
| Logs | Registro de todas las acciones ejecutadas para auditoría |

### 42.2 Políticas de Herramientas (Allow/Deny)

El administrador puede permitir o bloquear herramientas específicas:

```yaml
seguridad:
  tools:
    allow:
      - "*"  # Por defecto, todo permitido
    
    deny:
      - "exec.elevated"       # No ejecutar con privilegios
      - "browser.incognito"   # No navegación privada
    
    # Deny siempre gana sobre allow
    
  # Por contexto
  grupos:
    tools:
      deny:
        - "browser"   # Sin navegador en grupos
        - "nodes"     # Sin acceso a dispositivos
        - "exec"      # Sin ejecución de comandos
```

### 42.3 Sandbox vs Host Execution

G-Mini puede ejecutar herramientas en **sandbox (Docker)** o directamente en el **host**:

```
┌─────────────────────────────────────────────────────────────┐
│                    MODOS DE EJECUCIÓN                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐          ┌─────────────────┐           │
│  │   SANDBOX       │          │     HOST        │           │
│  │   (Docker)      │          │   (Directo)     │           │
│  │                 │          │                 │           │
│  │ • Aislado       │          │ • Acceso total  │           │
│  │ • Limitado      │          │ • Rápido        │           │
│  │ • Seguro        │          │ • Peligroso     │           │
│  │ • Lento         │          │                 │           │
│  └─────────────────┘          └─────────────────┘           │
│                                                              │
│  Modos:                                                      │
│  • off      → Todo en host (solo para uso personal)         │
│  • non-main → Sandbox en grupos, host en main               │
│  • all      → Todo en sandbox (máxima seguridad)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Configuración:**
```yaml
seguridad:
  sandbox:
    mode: "non-main"  # off | non-main | all
    
    docker:
      image: "gmini-sandbox:latest"
      memory_limit: "2GB"
      cpu_limit: "2"
      network: "none"  # Sin red en sandbox
      
    elevated:
      enabled: false      # No permitir escape de sandbox
      requires_approval: true
```

### 42.4 Modelo de Confianza

| Entidad | Nivel de Confianza | Permisos |
|---------|-------------------|----------|
| **Sesión Main** | Alto | Acceso completo (según config) |
| **Grupos** | Medio | Sandbox por defecto, tools limitados |
| **Nodes (propios)** | Alto | Acceso a superficies configuradas |
| **Nodes (externos)** | Bajo | Requiere aprobación explícita |
| **Skills** | Variable | Según permisos declarados |

### 42.5 Exec Approvals (Lista Blanca de Comandos)

Para ejecución remota en nodes, se usa una lista blanca:

```json
// exec-approvals.json
{
  "pc-casa": {
    "allowed_commands": [
      "python /home/user/scripts/backup.py",
      "python /home/user/scripts/sync.py",
      "systemctl status nginx"
    ],
    "allowed_patterns": [
      "^ls -la /home/user/.*",
      "^cat /home/user/logs/.*\\.log$"
    ],
    "denied_patterns": [
      "rm -rf",
      "sudo",
      "chmod 777"
    ]
  }
}
```

---

## 43. Fases de Desarrollo (MVP Incremental)

### Fase 1 — Core Foundation (~3-4 semanas)
**Objetivo:** Chat funcional con todos los proveedores de IA

- [ ] Estructura del proyecto (Electron + Python)
- [ ] Backend FastAPI con WebSocket
- [ ] Router de proveedores LLM (OpenAI, Anthropic, Google, xAI, DeepSeek)
- [ ] Soporte para modelos locales (Ollama, LM Studio)
- [ ] Frontend Electron: ventana principal + chat básico
- [ ] Comunicación bidireccional Electron ↔ Python
- [ ] Configuración básica (API keys, selección de modelo/proveedor)
- [ ] System tray icon
- [ ] Empaquetado básico (.exe)

**Entregable:** App que permite chatear con cualquier modelo (cloud + local).

### Fase 2 — Visión + Automatización (~4-5 semanas)
**Objetivo:** El agente puede ver y actuar sobre la pantalla

- [ ] Captura de pantalla (mss)
- [ ] Integración Tesseract OCR
- [ ] Integración EasyOCR + PaddleOCR
- [ ] Integración OmniParser (Microsoft)
- [ ] Modos de visión: Computer Use (imagen) vs Token Saver (solo texto)
- [ ] PyAutoGUI: click, write, scroll, hotkeys
- [ ] pynput: listeners de teclado
- [ ] Loop del agente (captura → análisis → LLM → acción → verificación)
- [ ] Preview en UI de lo que el agente ve
- [ ] Controles start/stop/pause
- [ ] ADB básico para Android (tap, swipe, screenshot)

**Entregable:** Agente autónomo que puede operar PC y Android ejecutando tareas.

### Fase 3 — Personaje + Voz (~4-5 semanas)
**Objetivo:** Asistente virtual animado con voz y todos los modos de interacción

- [ ] Overlay Electron transparente para personaje
- [ ] Animador de sprites 2D (4 estados: idle, talk, blink, blink_talk)
- [ ] Importador de sprites customizados
- [ ] MeloTTS integración (TTS offline)
- [ ] Análisis RMS para lipsync
- [ ] Renderer Three.js para modelos 3D (.glb)
- [ ] Botón 🎤 Speech-to-Text (Whisper local)
- [ ] Botón 📞 Voz Real-Time (OpenAI/Gemini/Grok APIs)
- [ ] Hover buttons en el overlay (💬🎤📞⚙️✖️)
- [ ] Drag, resize, click-through del overlay
- [ ] Configuración de personaje y voz en settings

**Entregable:** Asistente con personaje animado que habla, escucha, y conversa en tiempo real.

### Fase 4 — Sistema de Modos + Sub-Agentes (~4-5 semanas)
**Objetivo:** Capacidades de super-agente con modos especializados

- [ ] Sistema de modos (Normal, Programador, Marketero, Investigador, etc.)
- [ ] UI para cambiar de modo
- [ ] System prompts dinámicos por modo
- [ ] Arquitectura de sub-agentes
- [ ] Spawn y gestión de sub-agentes paralelos
- [ ] Comunicación entre agente principal y sub-agentes
- [ ] Panel de monitoreo de sub-agentes activos
- [ ] Permisos heredados y configurables por sub-agente
- [ ] Límites de recursos por sub-agente

**Entregable:** Agente con múltiples personalidades y capacidad multi-agente.

### Fase 5 — Integraciones Externas (~3-4 semanas)
**Objetivo:** Conexión con herramientas y servicios externos

- [ ] Integración navegador multi-perfil Chrome
- [ ] APIs de redes sociales (Facebook, Instagram, X, TikTok)
- [ ] Control de editores (CapCut, Premiere, ffmpeg)
- [ ] Control de herramientas de diseño (Canva, Figma)
- [ ] APIs de IA generativa (ElevenLabs, Runway, FlowGemini)
- [ ] APIs de OSINT (Hunter.io, Shodan, etc.)
- [ ] Conectores configurables (Notion, Slack, Google Calendar)

**Entregable:** Agente conectado al ecosistema de herramientas del usuario.

### Fase 6 — Gateway Multi-Canal (~3-4 semanas)
**Objetivo:** Comunicación desde múltiples plataformas

- [ ] Arquitectura del Gateway (WebSocket + router de sesiones)
- [ ] Bot de WhatsApp Web (recibir/enviar mensajes)
- [ ] Bot de Telegram (comandos, confirmaciones, screenshots)
- [ ] Integración Discord (bot, grupos, menciones)
- [ ] Integración Slack (mensajes, canales, acciones)
- [ ] Sesiones separadas por contexto (main vs grupos)
- [ ] Activación por mención en grupos
- [ ] Manejo de adjuntos (imágenes, PDFs, audio)
- [ ] Sistema de confirmación remota para acciones críticas

**Entregable:** Agente controlable desde WhatsApp, Telegram, Discord, Slack.

### Fase 7 — Sistema de Nodes (~4-5 semanas)
**Objetivo:** Dispositivos conectados como sensores y actuadores

- [ ] Arquitectura de Nodes (WebSocket + superficies)
- [ ] App companion iOS (camera, location, notifications, voice)
- [ ] App companion Android (camera, location, sms, contacts, device)
- [ ] Node host para PC remota (system, exec, files)
- [ ] Emparejamiento seguro de dispositivos
- [ ] Sistema de permisos por superficie
- [ ] Exec approvals (lista blanca de comandos)
- [ ] Panel de nodes conectados en UI

**Entregable:** Control de dispositivos móviles y PCs remotas.

### Fase 8 — Canvas + Skills + Cron (~4-5 semanas)
**Objetivo:** Dashboards, plugins y automatización programada

- [ ] Sistema Canvas (crear, actualizar, renderizar)
- [ ] Tipos de canvas (estado, dashboard, monitor, lista)
- [ ] Canvas en nodes (renderizar en dispositivos)
- [ ] Sistema de Skills (registry, instalación, configuración)
- [ ] Estructura de skills personalizadas
- [ ] Prioridad de skills (workspace → local → bundled)
- [ ] Sistema Cron (scheduler de tareas)
- [ ] Triggers: cron, intervalo, heartbeat, evento, webhook
- [ ] Panel de tareas programadas en UI

**Entregable:** Dashboards vivos, plugins extensibles, tareas automáticas.

### Fase 9 — Tareas 24/7 + Presupuesto (~3-4 semanas)
**Objetivo:** Operación continua y gestión de recursos

- [ ] Sistema de checkpoints para tareas largas
- [ ] Recuperación automática tras reinicio/crash
- [ ] Background jobs persistentes
- [ ] Panel de tareas 24/7 en UI
- [ ] Sistema de presupuesto y recursos
- [ ] Registro de cuentas/tarjetas con límites
- [ ] Permisos de gasto configurables

**Entregable:** Agente que opera 24/7 con gestión de recursos.

### Fase 10 — Seguridad + Pulido (~3-4 semanas)
**Objetivo:** Seguridad, sandboxing y producto final

- [ ] Políticas de herramientas (allow/deny)
- [ ] Sandbox Docker para ejecución aislada
- [ ] Modelo de confianza por contexto
- [ ] Restricciones éticas hardcodeadas
- [ ] Restricciones configurables por usuario
- [ ] Logging completo de acciones críticas
- [ ] Modo pentester con restricciones especiales
- [ ] Temas dark/light
- [ ] Inicio con Windows
- [ ] Empaquetado final con NSIS installer
- [ ] Manejo DPI + multi-monitor
- [ ] Documentación completa
- [ ] Testing end-to-end

**Entregable:** Producto final completo, seguro y pulido.

---

**Timeline Total Estimado:** 33-42 semanas (~8-10 meses)

**Nota:** Las fases pueden solaparse. Algunas tareas de fases posteriores pueden comenzarse antes si hay dependencias resueltas.

---

## 44. Dependencias Principales (Python)

```
# Core
fastapi>=0.110.0
uvicorn>=0.27.0
python-socketio>=5.11.0
pydantic>=2.6.0
pyyaml>=6.0

# LLM Providers
openai>=1.12.0
anthropic>=0.18.0
google-genai>=0.4.0

# Vision
mss>=9.0.0
pytesseract>=0.3.10
easyocr>=1.7.0
paddleocr>=2.7.0
paddlepaddle>=2.6.0

# ML
torch>=2.2.0
torchvision>=0.17.0

# OmniParser
ultralytics>=8.1.0          # YOLO para OmniParser

# Automation
pyautogui>=0.9.54
pynput>=1.7.6
Pillow>=10.2.0

# ADB
pure-python-adb>=0.3.0

# Voice
melotts>=0.1.0
sounddevice>=0.4.6
librosa>=0.10.0

# Speech-to-Text
faster-whisper>=1.0.0        # STT local (alternativa ligera a openai-whisper)

# Realtime Voice
websockets>=12.0             # Para conexiones WebSocket de voz real-time
xai-sdk>=0.1.0               # SDK oficial de xAI (Grok live voice)

# Gateway Multi-Canal
whatsapp-web.js>=1.23.0      # Vía subprocess Node.js
python-telegram-bot>=21.0    # Bot de Telegram
slack-sdk>=3.27.0            # Integración Slack
discord.py>=2.3.0            # Bot de Discord
matrix-nio>=0.24.0           # Cliente Matrix (opcional)

# Skills System
toml>=0.10.2                 # Parsing de skill.yaml
gitpython>=3.1.0             # Clonar skills desde repos

# Cron / Scheduler
apscheduler>=3.10.0          # Tareas programadas
croniter>=2.0.0              # Parsing de expresiones cron

# Canvas
jinja2>=3.1.0                # Templates para canvas HTML
markdown>=3.5.0              # Rendering de markdown

# Docker (Sandbox)
docker>=7.0.0                # Control de contenedores

# Utils
numpy>=1.26.0
keyring>=25.0.0
loguru>=0.7.0
aiohttp>=3.9.0               # HTTP async para APIs externas
aiofiles>=23.0.0             # File I/O async
```

---

## 45. Dependencias Frontend (Electron)

```json
{
  "dependencies": {
    "socket.io-client": "^4.7.0",
    "three": "^0.162.0",
    "pixi.js": "^8.0.0",
    "mermaid": "^10.0.0",
    "chart.js": "^4.4.0"
  },
  "devDependencies": {
    "electron": "^30.0.0",
    "electron-builder": "^24.0.0",
    "vite": "^5.0.0"
  }
}
```

---

## 46. Riesgos y Mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| 1 | Overlay intercepta clicks del agente | Alta | Alto | `pointer-events: none` + flag `click-through` durante automatización |
| 2 | Antivirus bloquea el .exe | Media | Alto | Firmar con certificado Code Signing; usar Nuitka como alternativa |
| 3 | Conflictos PyTorch + PaddlePaddle CUDA | Media | Alto | Ejecutar motores OCR en subprocesos separados si hay conflicto |
| 4 | DPI scaling rompe coordenadas | Alta | Medio | SetProcessDpiAwareness + escalar coordenadas |
| 5 | MeloTTS lento en CPU | Alta | Medio | Optimización: pipelining, pre-buffer, reducir calidad en CPU |
| 6 | Tamaño del instalador >5 GB | Alta | Bajo | Aceptado (decisión del usuario: todo incluido) |
| 7 | Electron + Python = proceso dual complejo | Media | Medio | Scripts de launch robustos; health checks bidireccionales |

---

## 47. KPIs de Éxito

| Métrica | Objetivo |
|---------|----------|
| Tiempo de respuesta del agente (texto) | < 3 segundos |
| Tiempo de captura + OCR | < 1 segundo |
| Precisión de clicks en elementos UI | > 90% |
| Latencia TTS (GPU) | < 2 segundos por frase |
| Inicio de la aplicación | < 10 segundos |
| Tasa de éxito en tareas simples (abrir app, buscar en web) | > 85% |

---

## 48. Glosario

| Término | Definición |
|---------|-----------|
| **LLM** | Large Language Model — modelo de lenguaje grande |
| **OCR** | Optical Character Recognition — reconocimiento óptico de caracteres |
| **TTS** | Text-to-Speech — síntesis de voz |
| **STT** | Speech-to-Text — convertir voz a texto |
| **OmniParser** | Herramienta de Microsoft para entender interfaces de usuario en screenshots |
| **ADB** | Android Debug Bridge — herramienta para comunicarse con dispositivos Android |
| **VRAM** | Video RAM — memoria de la tarjeta gráfica |
| **GGUF** | Formato de modelo cuantizado para inferencia local |
| **RMS** | Root Mean Square — medida de energía de una señal de audio |
| **MVP** | Minimum Viable Product — producto mínimo viable |
| **Realtime Voice** | Conversación bidireccional de voz en streaming con la IA |
| **Lipsync** | Sincronización labial — coordinar movimiento de boca con audio |
| **Whisper** | Modelo de reconocimiento de voz de OpenAI (funciona offline) |
| **Gateway** | Componente que enruta mensajes entre canales y sesiones del agente |
| **Node** | Dispositivo conectado que expone capacidades (cámara, ubicación, etc.) |
| **Superficie** | Conjunto de acciones expuestas por un node (ej: `camera.*`) |
| **Canvas** | Dashboard visual interactivo que se actualiza en tiempo real |
| **Skill** | Plugin instalable que extiende las capacidades del agente |
| **Cron** | Sistema de tareas programadas por horario |
| **Sandbox** | Entorno aislado (Docker) para ejecutar código de forma segura |
| **Session** | Contexto de conversación aislado (main, grupo, proyecto) |
| **Tool** | Herramienta que el agente puede invocar (exec, browser, etc.) |
| **Sub-agente** | Agente especializado creado por el agente principal para tareas paralelas |
| **Modo** | Configuración de personalidad y permisos del agente (Programador, Marketero, etc.) |
| **Checkpoint** | Punto de guardado del progreso de una tarea larga |
| **Heartbeat** | Señal periódica del sistema para verificar salud y disparar acciones |

---

*Documento generado el 5 de marzo de 2026. Listo para iniciar Fase 1.*
