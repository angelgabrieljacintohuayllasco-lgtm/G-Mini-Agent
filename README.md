# G-Mini Agent

Asistente IA que ve tu pantalla, hace clic y habla.

## Estructura

```
G-Mini-Agent/
├── backend/                  # Python — FastAPI + Socket.IO
│   ├── main.py              # Entry point
│   ├── config.py            # Configuración YAML + keyring
│   ├── requirements.txt     # Dependencias Python
│   ├── api/                 # REST + WebSocket handlers
│   │   ├── routes.py        # Endpoints REST
│   │   ├── schemas.py       # Pydantic models
│   │   └── websocket_handler.py
│   ├── core/                # Lógica central
│   │   ├── agent.py         # AgentCore — cerebro
│   │   ├── memory.py        # Historial + SQLite
│   │   ├── planner.py       # Planificador de acciones
│   │   └── token_manager.py # Conteo/truncado de tokens
│   ├── providers/           # LLM providers (7 total)
│   │   ├── base.py          # Clase abstracta
│   │   ├── openai_compat.py # OpenAI, xAI, DeepSeek, Ollama, LM Studio
│   │   ├── anthropic_provider.py
│   │   ├── google_provider.py
│   │   └── router.py        # Router con fallback
│   ├── vision/              # Phase 2 — Visión
│   │   ├── engine.py        # Captura + OCR
│   │   └── ui_detector.py   # Detección de elementos UI
│   ├── automation/          # Phase 2 — Automatización
│   │   ├── pc_controller.py # Mouse, teclado, scroll
│   │   └── adb_controller.py # Android via ADB
│   ├── voice/               # Phase 3 — Voz
│   │   ├── engine.py        # TTS + STT
│   │   └── realtime.py      # Voz en tiempo real
│   └── utils/
│       └── logger.py
├── electron/                 # Frontend — Electron
│   ├── main.js              # Main process
│   ├── preload.js           # Context bridge
│   ├── package.json
│   └── src/
│       ├── index.html       # UI principal
│       ├── overlay.html     # Overlay transparente
│       ├── css/main.css
│       └── js/
│           ├── app.js       # Controller principal
│           ├── websocket.js # Socket.IO client
│           ├── chat.js      # Chat rendering
│           └── settings.js  # Panel de configuración
├── config.default.yaml       # Configuración por defecto
├── start.bat                 # Script de inicio (Windows)
└── README.md
```

## Inicio Rápido

### Requisitos
- Python 3.11+
- Node.js 20+
- (Opcional) Tesseract OCR para visión

### Opción 1: Script automático
```bash
start.bat
```

### Opción 2: Manual
```bash
# Backend
python -m venv venv
venv\Scripts\activate
pip install -r backend\requirements.txt
python -m backend.main

# Frontend (otra terminal)
cd electron
npm install
npx electron .
```

## Configuración

### API Keys
Configura tus API keys desde el panel Settings de la UI, o via REST:
```bash
curl -X POST http://localhost:8765/api/api-keys \
  -H "Content-Type: application/json" \
  -d '{"vault_name": "openai_api_key", "api_key": "sk-..."}'
```

Las keys se almacenan en Windows Credential Manager (vía `keyring`).

### Proveedores soportados
| Provider | Tipo | Modelos |
|----------|------|---------|
| OpenAI | Cloud | gpt-4o, o3, o3-mini |
| Anthropic | Cloud | claude-sonnet-4, claude-haiku |
| Google | Cloud | gemini-2.0-flash, gemini-2.5-pro |
| xAI | Cloud | grok-3, grok-3-mini |
| DeepSeek | Cloud | deepseek-chat, deepseek-reasoner |
| Ollama | Local | llama3, mistral, etc. |
| LM Studio | Local | Cualquier modelo GGUF |

## Atajos de teclado
- `Alt+G` — Mostrar/ocultar ventana
- `Alt+Shift+G` — Toggle overlay
- `Ctrl+Shift+Q` — Cerrar aplicación
- `Ctrl+Shift+Esc` — Kill switch (detiene automatización)

## Fases
- **Phase 1**: Chat con 7 LLMs + UI Electron ✅
- **Phase 2**: Visión de pantalla + automatización PC/Android ✅
- **Phase 3**: Voz (TTS/STT) + voz en tiempo real ✅

## 🚀 Instalación desde GitHub

1. Clone el repo:
```bash
git clone https://github.com/tu-usuario/g-mini-agent.git
cd g-mini-agent
```

2. Instala dependencias:
```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd electron
npm install
```

3. Copia config:
```bash
cp config.user.yaml.example config.user.yaml
```

4. Configura API keys desde UI o REST (se guardan en Credential Manager)
5. Ejecuta:
```bash
start.bat
# o manual: python -m backend.main & cd electron && npx electron .
```

## 🔑 Seguridad - API Keys

- **NO** se almacenan en archivos
- Guardadas en **Windows Credential Manager** via `keyring`
- Configurar desde **Settings UI** o endpoint `/api/api-keys`
- `config.user.yaml` contiene solo preferencias (gitignore'd)

## 🤝 Contribuir

1. Fork → Clone → Create branch
2. `git checkout -b feature/nueva-funcion`
3. Commit → Push → Pull Request
4. Sigue [code style](#code-style)

### Code Style
- Python: black, isort, mypy
- JS: eslint, prettier

## 📄 Licencia

MIT License - ver LICENSE

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/link/?user=tu-usuario&repos=g-mini-agent)](https://star-history.com/#tu-usuario&g-mini-agent&Date)
