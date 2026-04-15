# Plan de Corrección Aprobado - G-Mini Agent

**Estado:** ✅ En Progreso

## 1. Corregir ImportError Backend [✅ COMPLETADO]
- [✅] `backend/core/modes.py` → Agregar `get_mode_behavior_prompt()`

## 2. Configurar Icono Correctamente [✅ COMPLETADO]  
- [✅] Copiar `G-mini Agent icon.png` → `electron/assets/icon.png`
- [✅] `electron/package.json` → Cambiar `"icon": "assets/icon.ico"` → `"icon": "assets/icon.png"`

## 2.1. Fixes Adicionales: Módulos Core Faltantes [🔄 EN PROCESO]
- [✅] `backend/core/mcp_registry.py` 
- [✅] `VALID_STDIO_TRANSPORTS`
- [✅] `backend/core/payment_registry.py`
- [✅] `backend/core/skill_runtime.py`

## 3. Verificación Final [🔄 TEST EN MARCHA]
- [ ] Backend arranca sin errores de import
- [ ] Icono correcto en taskbar/tray  
- [ ] UI + WebSocket funcionales
- [ ] Test: `cd electron && npx electron .` (backend sin errores)
- [ ] Test icono: Taskbar/Tray con icono correcto
- [ ] Test build: `npm run dist:win`

---

**Cambios realizados se marcarán con [✅]**
