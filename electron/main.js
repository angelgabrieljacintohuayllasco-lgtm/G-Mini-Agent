/**
 * G-Mini Agent — Electron Main Process
 * Ventana principal + overlay transparente + tray.
 * Lanza el backend Python como proceso hijo automáticamente.
 */

const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, screen } = require('electron');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const yaml = require('js-yaml');

let mainWindow = null;
let overlayWindow = null;
let tray = null;
let isOverlayMode = false;
let backendProcess = null;
let lastOverlayText = 'G-Mini Agent listo';

const BACKEND_URL = 'http://127.0.0.1:8765';
const BACKEND_HEALTH_URL = `${BACKEND_URL}/api/health`;
const BACKEND_START_TIMEOUT_MS = 60000;
const BACKEND_HEALTH_CHECK_INTERVAL_MS = 1000;
const BACKEND_HEALTH_REQUEST_TIMEOUT_MS = 1500;
const PROJECT_ROOT = path.resolve(__dirname, '..');
const DEFAULT_CONFIG_PATH = path.join(PROJECT_ROOT, 'config.default.yaml');
const USER_CONFIG_PATH = path.join(PROJECT_ROOT, 'config.user.yaml');
const OVERLAY_STATE_FILENAME = 'overlay-state.json';
const OVERLAY_BASE_SIZE = Object.freeze({ width: 400, height: 300 });
const OVERLAY_MIN_SCALE = 0.7;
const OVERLAY_MAX_SCALE = 2.25;
const OVERLAY_SAVE_DEBOUNCE_MS = 180;
const DEFAULT_APP_PREFERENCES = Object.freeze({
    startWithWindows: false,
    minimizeToTray: true,
    closeToTray: true,
    startHiddenToTray: false,
});
const DEFAULT_CHARACTER_PREFERENCES = Object.freeze({
    type: '2d',
    skin: 'default',
    defaultSize: 200,
    defaultOpacity: 100,
    blinkIntervalMinMs: 3000,
    blinkIntervalMaxMs: 5000,
    blinkDurationMs: 150,
});
const DEFAULT_OVERLAY_CHARACTER_RUNTIME = Object.freeze({
    status: 'idle',
    audioHintMs: 0,
    visemes: [],
    updatedAt: 0,
});

let appPreferences = { ...DEFAULT_APP_PREFERENCES };
let characterPreferences = { ...DEFAULT_CHARACTER_PREFERENCES };
let configReloadTimer = null;
let overlayRuntimeState = null;
let overlayStateSaveTimer = null;
let overlayInteractionLocked = false;
let overlayCharacterRuntime = { ...DEFAULT_OVERLAY_CHARACTER_RUNTIME };

function deepMerge(base, override) {
    const merged = { ...(base || {}) };
    for (const [key, value] of Object.entries(override || {})) {
        if (
            Object.prototype.hasOwnProperty.call(merged, key)
            && typeof merged[key] === 'object'
            && merged[key] !== null
            && !Array.isArray(merged[key])
            && typeof value === 'object'
            && value !== null
            && !Array.isArray(value)
        ) {
            merged[key] = deepMerge(merged[key], value);
        } else {
            merged[key] = value;
        }
    }
    return merged;
}

function readYamlConfig(filePath) {
    try {
        if (!fs.existsSync(filePath)) return {};
        return yaml.load(fs.readFileSync(filePath, 'utf8')) || {};
    } catch (err) {
        console.warn(`[Config] No se pudo leer ${path.basename(filePath)}: ${err.message}`);
        return {};
    }
}

function normalizeAppPreferences(rawAppConfig = {}) {
    return {
        startWithWindows: !!rawAppConfig.start_with_windows,
        minimizeToTray: rawAppConfig.minimize_to_tray !== false,
        closeToTray: rawAppConfig.close_to_tray !== false,
        startHiddenToTray: !!rawAppConfig.start_hidden_to_tray,
    };
}

function loadMergedProjectConfigFromDisk() {
    const defaults = readYamlConfig(DEFAULT_CONFIG_PATH);
    const overrides = readYamlConfig(USER_CONFIG_PATH);
    return deepMerge(defaults, overrides);
}

function normalizeCharacterPreferences(rawCharacterConfig = {}) {
    const defaultSize = clampNumber(toFiniteNumber(rawCharacterConfig.default_size, DEFAULT_CHARACTER_PREFERENCES.defaultSize), 120, 420);
    const defaultOpacity = clampNumber(toFiniteNumber(rawCharacterConfig.default_opacity, DEFAULT_CHARACTER_PREFERENCES.defaultOpacity), 35, 100);
    const blinkIntervalMinMs = clampNumber(
        Math.round(toFiniteNumber(rawCharacterConfig.blink_interval_min_s, DEFAULT_CHARACTER_PREFERENCES.blinkIntervalMinMs / 1000) * 1000),
        1200,
        12000
    );
    const blinkIntervalMaxMs = clampNumber(
        Math.round(toFiniteNumber(rawCharacterConfig.blink_interval_max_s, DEFAULT_CHARACTER_PREFERENCES.blinkIntervalMaxMs / 1000) * 1000),
        blinkIntervalMinMs,
        16000
    );
    const blinkDurationMs = clampNumber(
        Math.round(toFiniteNumber(rawCharacterConfig.blink_duration_ms, DEFAULT_CHARACTER_PREFERENCES.blinkDurationMs)),
        60,
        900
    );

    return {
        type: String(rawCharacterConfig.type || DEFAULT_CHARACTER_PREFERENCES.type),
        skin: String(rawCharacterConfig.skin || DEFAULT_CHARACTER_PREFERENCES.skin),
        defaultSize,
        defaultOpacity,
        blinkIntervalMinMs,
        blinkIntervalMaxMs,
        blinkDurationMs,
    };
}

function loadAppPreferencesFromDisk() {
    const merged = loadMergedProjectConfigFromDisk();
    return normalizeAppPreferences(merged.app || {});
}

function loadCharacterPreferencesFromDisk() {
    const merged = loadMergedProjectConfigFromDisk();
    return normalizeCharacterPreferences(merged.character || {});
}

function getEffectiveAppRuntimeSettings() {
    const canApplyStartWithWindows = process.platform === 'win32' && app.isPackaged;
    let loginItemEnabled = false;

    try {
        if (process.platform === 'win32') {
            loginItemEnabled = !!app.getLoginItemSettings().openAtLogin;
        }
    } catch (err) {
        loginItemEnabled = false;
    }

    return {
        ...appPreferences,
        canApplyStartWithWindows,
        startWithWindowsApplied: canApplyStartWithWindows ? loginItemEnabled : false,
        isPackaged: app.isPackaged,
        platform: process.platform,
    };
}

function applyStartWithWindowsSetting() {
    if (process.platform !== 'win32') return;

    if (!app.isPackaged) {
        if (appPreferences.startWithWindows) {
            console.warn('[App] Inicio con Windows solicitado, pero solo se aplica automaticamente en builds empaquetadas.');
        }
        return;
    }

    try {
        app.setLoginItemSettings({
            openAtLogin: !!appPreferences.startWithWindows,
        });
    } catch (err) {
        console.error(`[App] No se pudo actualizar inicio con Windows: ${err.message}`);
    }
}

function refreshTrayMenu() {
    if (!tray) return;

    const behaviorSummary = appPreferences.closeToTray
        ? 'Cerrar -> bandeja'
        : 'Cerrar -> salir';
    const minimizeSummary = appPreferences.minimizeToTray
        ? 'Minimizar -> bandeja'
        : 'Minimizar normal';

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Mostrar G-Mini Agent',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                    mainWindow.focus();
                }
            },
        },
        {
            label: behaviorSummary,
            enabled: false,
        },
        {
            label: minimizeSummary,
            enabled: false,
        },
        {
            label: 'Modo Overlay',
            type: 'checkbox',
            checked: isOverlayMode,
            click: (item) => {
                toggleOverlay(item.checked);
            },
        },
        { type: 'separator' },
        {
            label: 'Salir',
            click: () => {
                app.isQuitting = true;
                app.quit();
            },
        },
    ]);

    tray.setContextMenu(contextMenu);
}

function applyAppPreferences(nextPreferences = null) {
    appPreferences = {
        ...DEFAULT_APP_PREFERENCES,
        ...(nextPreferences || loadAppPreferencesFromDisk()),
    };

    if (app.isReady()) {
        applyStartWithWindowsSetting();
        refreshTrayMenu();
    }
}

function applyCharacterPreferences(nextPreferences = null) {
    characterPreferences = {
        ...DEFAULT_CHARACTER_PREFERENCES,
        ...(nextPreferences || loadCharacterPreferencesFromDisk()),
    };
    broadcastOverlayState();
}

function reloadRuntimePreferencesFromDisk() {
    const mergedConfig = loadMergedProjectConfigFromDisk();
    applyAppPreferences(normalizeAppPreferences(mergedConfig.app || {}));
    applyCharacterPreferences(normalizeCharacterPreferences(mergedConfig.character || {}));
}

function scheduleAppPreferencesReload() {
    clearTimeout(configReloadTimer);
    configReloadTimer = setTimeout(() => {
        try {
            reloadRuntimePreferencesFromDisk();
        } catch (err) {
            console.error(`[Config] Error recargando preferencias app: ${err.message}`);
        }
    }, 150);
}

function watchConfigFiles() {
    fs.watchFile(DEFAULT_CONFIG_PATH, { interval: 1200 }, scheduleAppPreferencesReload);
    fs.watchFile(USER_CONFIG_PATH, { interval: 1200 }, scheduleAppPreferencesReload);
}

function unwatchConfigFiles() {
    fs.unwatchFile(DEFAULT_CONFIG_PATH, scheduleAppPreferencesReload);
    fs.unwatchFile(USER_CONFIG_PATH, scheduleAppPreferencesReload);
}

reloadRuntimePreferencesFromDisk();

function getOverlayStatePath() {
    return path.join(app.getPath('userData'), OVERLAY_STATE_FILENAME);
}

function toFiniteNumber(value, fallback) {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : fallback;
}

function clampNumber(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function getOverlayDisplayBounds(display) {
    if (display?.workArea && Number.isFinite(display.workArea.width) && Number.isFinite(display.workArea.height)) {
        return display.workArea;
    }
    if (display?.bounds) return display.bounds;
    return screen.getPrimaryDisplay().workArea;
}

function getDefaultOverlayBounds(display = null, scale = 1.0) {
    const targetDisplay = display || screen.getPrimaryDisplay();
    const workArea = getOverlayDisplayBounds(targetDisplay);
    const normalizedScale = clampNumber(toFiniteNumber(scale, 1.0), OVERLAY_MIN_SCALE, OVERLAY_MAX_SCALE);
    const width = Math.round(OVERLAY_BASE_SIZE.width * normalizedScale);
    const height = Math.round(OVERLAY_BASE_SIZE.height * normalizedScale);
    return {
        x: Math.round(workArea.x + workArea.width - width - 20),
        y: Math.round(workArea.y + workArea.height - height - 20),
        width,
        height,
    };
}

function getAllDisplaysSafe() {
    try {
        return screen.getAllDisplays();
    } catch (err) {
        console.warn(`[Overlay] No se pudo leer displays: ${err.message}`);
        return [screen.getPrimaryDisplay()];
    }
}

function getDisplayById(displayId) {
    return getAllDisplaysSafe().find((display) => display.id === displayId) || null;
}

function hasVisibleIntersection(bounds) {
    return getAllDisplaysSafe().some((display) => {
        const area = getOverlayDisplayBounds(display);
        const overlapWidth = Math.min(bounds.x + bounds.width, area.x + area.width) - Math.max(bounds.x, area.x);
        const overlapHeight = Math.min(bounds.y + bounds.height, area.y + area.height) - Math.max(bounds.y, area.y);
        return overlapWidth > 0 && overlapHeight > 0;
    });
}

function normalizeOverlayBounds(rawBounds, preferredDisplayId = null) {
    const preferredDisplay = preferredDisplayId !== null ? getDisplayById(preferredDisplayId) : null;
    const fallbackDisplay = preferredDisplay || screen.getPrimaryDisplay();
    const desiredWidth = toFiniteNumber(rawBounds?.width, OVERLAY_BASE_SIZE.width);
    const inferredScale = desiredWidth / OVERLAY_BASE_SIZE.width;
    const scale = clampNumber(toFiniteNumber(rawBounds?.scale, inferredScale), OVERLAY_MIN_SCALE, OVERLAY_MAX_SCALE);
    const width = Math.round(OVERLAY_BASE_SIZE.width * scale);
    const height = Math.round(OVERLAY_BASE_SIZE.height * scale);
    const rawX = Math.round(toFiniteNumber(rawBounds?.x, getDefaultOverlayBounds(fallbackDisplay, scale).x));
    const rawY = Math.round(toFiniteNumber(rawBounds?.y, getDefaultOverlayBounds(fallbackDisplay, scale).y));
    const provisionalBounds = { x: rawX, y: rawY, width, height };

    if (!hasVisibleIntersection(provisionalBounds)) {
        const resetBounds = getDefaultOverlayBounds(fallbackDisplay, scale);
        return {
            ...resetBounds,
            scale,
            displayId: fallbackDisplay.id,
        };
    }

    const matchedDisplay = screen.getDisplayMatching(provisionalBounds) || fallbackDisplay;
    const workArea = getOverlayDisplayBounds(matchedDisplay);
    const clampedWidth = Math.min(width, workArea.width);
    const clampedHeight = Math.min(height, workArea.height);
    const finalScale = clampNumber(
        Math.min(clampedWidth / OVERLAY_BASE_SIZE.width, clampedHeight / OVERLAY_BASE_SIZE.height),
        OVERLAY_MIN_SCALE,
        OVERLAY_MAX_SCALE
    );
    const finalWidth = Math.round(OVERLAY_BASE_SIZE.width * finalScale);
    const finalHeight = Math.round(OVERLAY_BASE_SIZE.height * finalScale);
    const x = clampNumber(rawX, workArea.x, workArea.x + workArea.width - finalWidth);
    const y = clampNumber(rawY, workArea.y, workArea.y + workArea.height - finalHeight);

    return {
        x,
        y,
        width: finalWidth,
        height: finalHeight,
        scale: finalScale,
        displayId: matchedDisplay.id,
    };
}

function sanitizeCharacterRuntimeUpdate(payload = {}) {
    const nextState = {
        ...overlayCharacterRuntime,
    };

    if (typeof payload.status === 'string' && payload.status.trim()) {
        nextState.status = payload.status.trim().toLowerCase();
    }

    if (Number.isFinite(Number(payload.audioHintMs))) {
        nextState.audioHintMs = Math.max(0, Math.round(Number(payload.audioHintMs)));
    }

    if (Array.isArray(payload.visemes)) {
        nextState.visemes = payload.visemes
            .filter((entry) => entry && Number.isFinite(Number(entry.time)))
            .map((entry) => ({
                time: Number(entry.time),
                viseme: String(entry.viseme || 'rest'),
                weight: Number.isFinite(Number(entry.weight)) ? Number(entry.weight) : 0.0,
            }));
    }

    nextState.updatedAt = Number.isFinite(Number(payload.updatedAt))
        ? Number(payload.updatedAt)
        : Date.now();

    return nextState;
}

function getOverlayStateSnapshot() {
    const fallbackBounds = getDefaultOverlayBounds();
    const activeBounds = overlayWindow && !overlayWindow.isDestroyed()
        ? overlayWindow.getBounds()
        : (overlayRuntimeState?.bounds || fallbackBounds);

    return {
        interactive: !!overlayRuntimeState?.interactive && !overlayInteractionLocked,
        requestedInteractive: !!overlayRuntimeState?.interactive,
        lockedPassive: overlayInteractionLocked,
        visible: !!(overlayWindow && !overlayWindow.isDestroyed() && overlayWindow.isVisible()),
        displayId: overlayRuntimeState?.displayId ?? null,
        scale: overlayRuntimeState?.scale ?? 1.0,
        bounds: activeBounds,
        minScale: OVERLAY_MIN_SCALE,
        maxScale: OVERLAY_MAX_SCALE,
        baseWidth: OVERLAY_BASE_SIZE.width,
        baseHeight: OVERLAY_BASE_SIZE.height,
        characterConfig: characterPreferences,
        characterRuntime: overlayCharacterRuntime,
    };
}

function persistOverlayStateToDisk() {
    if (!app.isReady() || !overlayRuntimeState) return;

    try {
        fs.mkdirSync(app.getPath('userData'), { recursive: true });
        fs.writeFileSync(
            getOverlayStatePath(),
            JSON.stringify({
                bounds: overlayRuntimeState.bounds,
                scale: overlayRuntimeState.scale,
                displayId: overlayRuntimeState.displayId,
            }, null, 2),
            'utf8'
        );
    } catch (err) {
        console.error(`[Overlay] No se pudo persistir estado: ${err.message}`);
    }
}

function scheduleOverlayStatePersist() {
    clearTimeout(overlayStateSaveTimer);
    overlayStateSaveTimer = setTimeout(() => {
        persistOverlayStateToDisk();
    }, OVERLAY_SAVE_DEBOUNCE_MS);
}

function loadOverlayStateFromDisk() {
    const fallbackBounds = getDefaultOverlayBounds();
    const fallbackState = {
        interactive: false,
        scale: 1.0,
        displayId: screen.getPrimaryDisplay().id,
        bounds: fallbackBounds,
    };

    try {
        const statePath = getOverlayStatePath();
        if (!fs.existsSync(statePath)) return fallbackState;
        const rawState = JSON.parse(fs.readFileSync(statePath, 'utf8'));
        const normalizedBounds = normalizeOverlayBounds(rawState?.bounds || rawState, rawState?.displayId ?? null);
        return {
            interactive: false,
            scale: normalizedBounds.scale,
            displayId: normalizedBounds.displayId,
            bounds: {
                x: normalizedBounds.x,
                y: normalizedBounds.y,
                width: normalizedBounds.width,
                height: normalizedBounds.height,
            },
        };
    } catch (err) {
        console.warn(`[Overlay] No se pudo cargar estado persistido: ${err.message}`);
        return fallbackState;
    }
}

function updateOverlayWindowInteractivity() {
    if (!overlayWindow || overlayWindow.isDestroyed()) return;

    const shouldIgnoreMouse = overlayInteractionLocked || !overlayRuntimeState?.interactive;

    try {
        overlayWindow.setIgnoreMouseEvents(shouldIgnoreMouse, { forward: true });
    } catch (err) {
        console.error(`[Overlay] No se pudo actualizar click-through: ${err.message}`);
    }

    if (typeof overlayWindow.setFocusable === 'function') {
        try {
            overlayWindow.setFocusable(!shouldIgnoreMouse);
        } catch (err) {
            console.warn(`[Overlay] No se pudo actualizar focusable: ${err.message}`);
        }
    }
}

function broadcastOverlayState() {
    if (!overlayWindow || overlayWindow.isDestroyed()) return;
    overlayWindow.webContents.send('overlay-state', getOverlayStateSnapshot());
}

function commitOverlayBounds(nextBounds, options = {}) {
    if (!overlayWindow || overlayWindow.isDestroyed()) return getOverlayStateSnapshot();

    const normalizedBounds = normalizeOverlayBounds(nextBounds, options.displayId ?? overlayRuntimeState?.displayId ?? null);
    const finalBounds = {
        x: normalizedBounds.x,
        y: normalizedBounds.y,
        width: normalizedBounds.width,
        height: normalizedBounds.height,
    };

    overlayRuntimeState = {
        ...(overlayRuntimeState || {}),
        interactive: !!overlayRuntimeState?.interactive,
        bounds: finalBounds,
        scale: normalizedBounds.scale,
        displayId: normalizedBounds.displayId,
    };

    overlayWindow.setBounds(finalBounds, Boolean(options.animate));
    scheduleOverlayStatePersist();
    broadcastOverlayState();
    return getOverlayStateSnapshot();
}

function setOverlayInteractive(nextInteractive, options = {}) {
    if (!overlayRuntimeState) {
        overlayRuntimeState = loadOverlayStateFromDisk();
    }

    overlayRuntimeState = {
        ...overlayRuntimeState,
        interactive: overlayInteractionLocked && !options.force ? false : !!nextInteractive,
    };

    updateOverlayWindowInteractivity();
    broadcastOverlayState();
    return getOverlayStateSnapshot();
}

function setOverlayInteractionLocked(locked) {
    overlayInteractionLocked = !!locked;
    if (overlayInteractionLocked && overlayRuntimeState?.interactive) {
        overlayRuntimeState = {
            ...overlayRuntimeState,
            interactive: false,
        };
    }
    updateOverlayWindowInteractivity();
    broadcastOverlayState();
}

function setOverlayCharacterRuntime(payload = {}) {
    overlayCharacterRuntime = sanitizeCharacterRuntimeUpdate(payload);
    if (overlayWindow && !overlayWindow.isDestroyed()) {
        overlayWindow.webContents.send('overlay-character-runtime', overlayCharacterRuntime);
    }
    broadcastOverlayState();
    return overlayCharacterRuntime;
}

async function isBackendHealthy() {
    let timeoutId = null;
    try {
        const controller = new AbortController();
        timeoutId = setTimeout(() => controller.abort(), BACKEND_HEALTH_REQUEST_TIMEOUT_MS);
        const response = await fetch(BACKEND_HEALTH_URL, {
            method: 'GET',
            cache: 'no-store',
            signal: controller.signal,
        });
        return response.ok;
    } catch (err) {
        return false;
    } finally {
        if (timeoutId) clearTimeout(timeoutId);
    }
}

// ── Backend Process Management ───────────────────────────────

function startBackend() {
    return new Promise((resolve) => {
        const venvPython = path.join(PROJECT_ROOT, 'venv', 'Scripts', 'python.exe');
        const fallbackPython = 'python';

        // Intentar con el venv primero, fallback a python global
        const pythonPath = fs.existsSync(venvPython) ? venvPython : fallbackPython;

        console.log(`[Backend] Iniciando con: ${pythonPath}`);

        backendProcess = spawn(pythonPath, ['-m', 'backend.main'], {
            cwd: PROJECT_ROOT,
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        let started = false;
        let settled = false;
        let healthCheckInFlight = false;
        let healthPollTimer = null;
        let timeoutHandle = null;

        const finish = (ok) => {
            if (settled) return;
            settled = true;
            if (healthPollTimer) clearInterval(healthPollTimer);
            if (timeoutHandle) clearTimeout(timeoutHandle);
            resolve(ok);
        };

        const probeHealth = async () => {
            if (settled || started || !backendProcess || healthCheckInFlight) return;
            healthCheckInFlight = true;
            try {
                const healthy = await isBackendHealthy();
                if (healthy && !started) {
                    started = true;
                    finish(true);
                }
            } finally {
                healthCheckInFlight = false;
            }
        };

        backendProcess.stdout.on('data', (data) => {
            const text = data.toString();
            process.stdout.write(`[Backend] ${text}`);
        });

        backendProcess.stderr.on('data', (data) => {
            process.stderr.write(`[Backend] ${data.toString()}`);
        });

        backendProcess.on('error', (err) => {
            console.error(`[Backend] Error al iniciar: ${err.message}`);
            if (!started) finish(false);
        });

        backendProcess.on('exit', (code) => {
            console.log(`[Backend] Proceso termin? con c?digo: ${code}`);
            backendProcess = null;
            if (!started) finish(false);
        });

        healthPollTimer = setInterval(() => {
            void probeHealth();
        }, BACKEND_HEALTH_CHECK_INTERVAL_MS);
        void probeHealth();

        // Timeout: si no arranca en 60s, continuar igual
        timeoutHandle = setTimeout(() => {
            if (!started) {
                console.warn('[Backend] Timeout esperando arranque, continuando...');
                finish(false);
            }
        }, BACKEND_START_TIMEOUT_MS);
    });
}

function stopBackend() {
    if (backendProcess) {
        console.log('[Backend] Deteniendo...');
        backendProcess.kill('SIGTERM');
        // Forzar kill si no termina en 3s
        setTimeout(() => {
            if (backendProcess) {
                backendProcess.kill('SIGKILL');
                backendProcess = null;
            }
        }, 3000);
    }
}

// ── Main Window ──────────────────────────────────────────────

function createMainWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: 420,
        height: 700,
        minWidth: 360,
        minHeight: 500,
        x: width - 440,
        y: height - 720,
        frame: false,
        transparent: false,
        resizable: true,
        alwaysOnTop: true,
        skipTaskbar: false,
        show: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
        title: 'G-Mini Agent',
    });

    mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

    mainWindow.once('ready-to-show', () => {
        if (!appPreferences.startHiddenToTray) {
            mainWindow.show();
            mainWindow.focus();
        }
    });

    mainWindow.on('minimize', (e) => {
        if (appPreferences.minimizeToTray && !app.isQuitting) {
            e.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('close', (e) => {
        if (!app.isQuitting && appPreferences.closeToTray) {
            e.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // DevTools en modo dev
    if (process.argv.includes('--dev')) {
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
}

// ── Overlay Window (transparente, click-through) ────────────

function createOverlayWindow() {
    overlayRuntimeState = loadOverlayStateFromDisk();
    const overlayBounds = overlayRuntimeState.bounds || getDefaultOverlayBounds();

    overlayWindow = new BrowserWindow({
        width: overlayBounds.width,
        height: overlayBounds.height,
        x: overlayBounds.x,
        y: overlayBounds.y,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        focusable: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    overlayWindow.loadFile(path.join(__dirname, 'src', 'overlay.html'));
    overlayWindow.setVisibleOnAllWorkspaces(true);
    overlayWindow.hide();
    updateOverlayWindowInteractivity();

    overlayWindow.webContents.on('did-finish-load', () => {
        overlayWindow.webContents.send('overlay-text', lastOverlayText);
        broadcastOverlayState();
    });

    overlayWindow.on('move', () => {
        if (overlayWindow.isDestroyed()) return;
        const bounds = overlayWindow.getBounds();
        const normalizedBounds = normalizeOverlayBounds(bounds, overlayRuntimeState?.displayId ?? null);
        overlayRuntimeState = {
            ...(overlayRuntimeState || {}),
            interactive: !!overlayRuntimeState?.interactive,
            scale: normalizedBounds.scale,
            displayId: normalizedBounds.displayId,
            bounds: {
                x: bounds.x,
                y: bounds.y,
                width: bounds.width,
                height: bounds.height,
            },
        };
        scheduleOverlayStatePersist();
        broadcastOverlayState();
    });

    overlayWindow.on('resize', () => {
        if (overlayWindow.isDestroyed()) return;
        const bounds = overlayWindow.getBounds();
        const normalizedBounds = normalizeOverlayBounds(bounds, overlayRuntimeState?.displayId ?? null);
        overlayRuntimeState = {
            ...(overlayRuntimeState || {}),
            interactive: !!overlayRuntimeState?.interactive,
            scale: normalizedBounds.scale,
            displayId: normalizedBounds.displayId,
            bounds: {
                x: bounds.x,
                y: bounds.y,
                width: bounds.width,
                height: bounds.height,
            },
        };
        scheduleOverlayStatePersist();
        broadcastOverlayState();
    });

    overlayWindow.on('closed', () => {
        overlayWindow = null;
    });
}

// ── Tray ─────────────────────────────────────────────────────

function createTray() {
    const { nativeImage } = require('electron');
    const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
    let icon;

    try {
        const fs = require('fs');
        if (fs.existsSync(iconPath)) {
            icon = nativeImage.createFromPath(iconPath);
        } else {
            // Crear un icono 16x16 simple (cuadrado verde) como fallback
            icon = nativeImage.createFromBuffer(
                Buffer.from('iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMElEQVQ4T2Nk+M/wn4EIwMjIyMhAjAGMo' +
                    'AYMXRdgGEDMixg1YBi8BiDYAkKjAQCx0QkR8R2CSAAAAABJRU5ErkJggg==', 'base64')
            );
        }
    } catch (e) {
        icon = nativeImage.createEmpty();
    }
    
    tray = new Tray(icon);

    tray.setToolTip('G-Mini Agent');
    refreshTrayMenu();

    tray.on('click', () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.focus();
            } else {
                mainWindow.show();
            }
        }
    });
}

// ── Overlay Toggle ───────────────────────────────────────────

function toggleOverlay(enable) {
    isOverlayMode = enable;
    if (!overlayWindow || overlayWindow.isDestroyed()) {
        createOverlayWindow();
    }
    if (enable) {
        if (overlayWindow) {
            setOverlayInteractive(false, { force: true });
            if (typeof overlayWindow.showInactive === 'function') {
                overlayWindow.showInactive();
            } else {
                overlayWindow.show();
            }
            broadcastOverlayState();
        }
    } else {
        if (overlayWindow) {
            setOverlayInteractive(false, { force: true });
            overlayWindow.hide();
        }
    }
    refreshTrayMenu();
}

// ── IPC Handlers ─────────────────────────────────────────────

ipcMain.handle('get-backend-url', () => BACKEND_URL);

ipcMain.handle('minimize-window', () => {
    if (mainWindow) mainWindow.minimize();
});

ipcMain.handle('close-window', () => {
    if (mainWindow) mainWindow.close();
});

ipcMain.handle('toggle-always-on-top', (_, value) => {
    if (mainWindow) mainWindow.setAlwaysOnTop(value);
});

ipcMain.handle('toggle-overlay', (_, enable) => {
    toggleOverlay(enable);
    return getOverlayStateSnapshot();
});

ipcMain.handle('set-overlay-text', (_, text) => {
    lastOverlayText = String(text || '');
    if (overlayWindow) {
        overlayWindow.webContents.send('overlay-text', lastOverlayText);
    }
    return { success: true };
});

ipcMain.handle('overlay:get-state', () => {
    return getOverlayStateSnapshot();
});

ipcMain.handle('overlay:set-interactive', (_, interactive) => {
    return setOverlayInteractive(interactive);
});

ipcMain.handle('overlay:set-character-runtime', (_, payload = {}) => {
    return setOverlayCharacterRuntime(payload);
});

ipcMain.handle('overlay:move-by', (_, dx, dy) => {
    if (!overlayWindow || overlayWindow.isDestroyed()) {
        return getOverlayStateSnapshot();
    }
    const bounds = overlayWindow.getBounds();
    return commitOverlayBounds({
        x: Math.round(bounds.x + toFiniteNumber(dx, 0)),
        y: Math.round(bounds.y + toFiniteNumber(dy, 0)),
        width: bounds.width,
        height: bounds.height,
    });
});

ipcMain.handle('overlay:resize-by', (_, delta, anchor = 'center') => {
    if (!overlayWindow || overlayWindow.isDestroyed()) {
        return getOverlayStateSnapshot();
    }

    const currentBounds = overlayWindow.getBounds();
    const currentScale = clampNumber(
        toFiniteNumber(overlayRuntimeState?.scale, currentBounds.width / OVERLAY_BASE_SIZE.width),
        OVERLAY_MIN_SCALE,
        OVERLAY_MAX_SCALE
    );
    const nextScale = clampNumber(currentScale + toFiniteNumber(delta, 0), OVERLAY_MIN_SCALE, OVERLAY_MAX_SCALE);
    const nextWidth = Math.round(OVERLAY_BASE_SIZE.width * nextScale);
    const nextHeight = Math.round(OVERLAY_BASE_SIZE.height * nextScale);
    const widthDelta = nextWidth - currentBounds.width;
    const heightDelta = nextHeight - currentBounds.height;

    let nextX = currentBounds.x;
    let nextY = currentBounds.y;

    if (anchor === 'top-left') {
        nextX = currentBounds.x;
        nextY = currentBounds.y;
    } else if (anchor === 'bottom-right') {
        nextX = currentBounds.x - widthDelta;
        nextY = currentBounds.y - heightDelta;
    } else {
        nextX = currentBounds.x - Math.round(widthDelta / 2);
        nextY = currentBounds.y - Math.round(heightDelta / 2);
    }

    return commitOverlayBounds({
        x: nextX,
        y: nextY,
        width: nextWidth,
        height: nextHeight,
    });
});

ipcMain.handle('overlay:set-bounds', (_, rawBounds = {}) => {
    if (!overlayWindow || overlayWindow.isDestroyed()) {
        return getOverlayStateSnapshot();
    }
    return commitOverlayBounds(rawBounds);
});

ipcMain.handle('get-app-runtime-settings', () => {
    return getEffectiveAppRuntimeSettings();
});

ipcMain.handle('reload-app-runtime-settings', () => {
    applyAppPreferences(loadAppPreferencesFromDisk());
    return getEffectiveAppRuntimeSettings();
});

// ── Effect Handlers (Click indicators, Screenshot overlay, Transparency) ────

let actionOverlayWindow = null;

function createActionOverlayWindow() {
    const { width, height } = screen.getPrimaryDisplay().size;

    actionOverlayWindow = new BrowserWindow({
        width: width,
        height: height,
        x: 0,
        y: 0,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        focusable: false,
        hasShadow: false,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    // Cargar HTML inline para el overlay de acciones
    actionOverlayWindow.loadURL(`data:text/html,
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                background: transparent; 
                overflow: hidden;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }

            /* ── Click Indicator ── */
            .click-point {
                position: fixed;
                pointer-events: none;
                z-index: 10000;
                transform: translate(-50%, -50%);
            }
            .click-point .dot {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: #6366f1;
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                box-shadow: 0 0 12px rgba(99, 102, 241, 0.8), 0 0 24px rgba(99, 102, 241, 0.4);
                animation: dot-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
            }
            .click-point .ripple {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0);
                border-radius: 50%;
                border: 2.5px solid rgba(99, 102, 241, 0.7);
                pointer-events: none;
            }
            .click-point .ripple-1 {
                width: 50px;
                height: 50px;
                animation: ripple-out 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
            }
            .click-point .ripple-2 {
                width: 80px;
                height: 80px;
                animation: ripple-out 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.1s forwards;
            }
            .click-point .ripple-3 {
                width: 120px;
                height: 120px;
                animation: ripple-out 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.2s forwards;
            }
            .click-point .coord-label {
                position: absolute;
                top: -32px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(30, 30, 40, 0.85);
                color: #a5b4fc;
                font-size: 11px;
                font-weight: 600;
                padding: 3px 10px;
                border-radius: 6px;
                white-space: nowrap;
                backdrop-filter: blur(6px);
                border: 1px solid rgba(99, 102, 241, 0.3);
                animation: label-fade 0.8s ease forwards;
                letter-spacing: 0.5px;
            }

            /* Double click — second ring */
            .click-point.double_click .ripple-1 { animation-iteration-count: 2; }
            .click-point.double_click .dot { background: #818cf8; }

            /* Right click — orange tint */
            .click-point.right_click .dot { background: #f59e0b; box-shadow: 0 0 12px rgba(245, 158, 11, 0.8); }
            .click-point.right_click .ripple { border-color: rgba(245, 158, 11, 0.6); }
            .click-point.right_click .coord-label { color: #fcd34d; border-color: rgba(245, 158, 11, 0.3); }

            @keyframes dot-pop {
                0% { transform: translate(-50%, -50%) scale(0); opacity: 1; }
                40% { transform: translate(-50%, -50%) scale(1.4); opacity: 1; }
                100% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
            }
            @keyframes ripple-out {
                0% { transform: translate(-50%, -50%) scale(0); opacity: 0.8; }
                100% { transform: translate(-50%, -50%) scale(1); opacity: 0; }
            }
            @keyframes label-fade {
                0% { opacity: 0; transform: translateX(-50%) translateY(6px); }
                20% { opacity: 1; transform: translateX(-50%) translateY(0); }
                70% { opacity: 1; }
                100% { opacity: 0; }
            }

            /* ── Screenshot Overlay (phone-style) ── */
            #screenshot-overlay {
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                pointer-events: none;
                z-index: 9999;
                display: none;
            }
            #screenshot-overlay.active {
                display: block;
            }
            #screenshot-overlay .flash {
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                background: white;
                animation: ss-flash 0.35s ease-out forwards;
            }
            #screenshot-overlay .border-frame {
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                border: 4px solid #6366f1;
                border-radius: 0;
                animation: ss-border 0.8s ease-out forwards;
                box-shadow: inset 0 0 60px rgba(99, 102, 241, 0.15);
            }
            #screenshot-overlay .badge {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.8);
                background: rgba(20, 20, 30, 0.88);
                backdrop-filter: blur(12px);
                color: white;
                padding: 14px 28px;
                border-radius: 14px;
                font-size: 16px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(99, 102, 241, 0.3);
                animation: ss-badge 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
                letter-spacing: 0.3px;
            }
            #screenshot-overlay .badge .icon {
                font-size: 22px;
                filter: drop-shadow(0 0 4px rgba(99, 102, 241, 0.5));
            }
            #screenshot-overlay .shutter-line {
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 3px;
                background: linear-gradient(90deg, transparent, #6366f1, #818cf8, #6366f1, transparent);
                animation: ss-shutter 0.5s ease-out forwards;
            }
            @keyframes ss-flash {
                0% { opacity: 0.7; }
                100% { opacity: 0; }
            }
            @keyframes ss-border {
                0% { opacity: 1; border-width: 4px; }
                40% { opacity: 1; }
                100% { opacity: 0; border-width: 0; }
            }
            @keyframes ss-badge {
                0% { opacity: 0; transform: translate(-50%, -50%) scale(0.6); }
                30% { opacity: 1; transform: translate(-50%, -50%) scale(1.05); }
                50% { transform: translate(-50%, -50%) scale(1); }
                80% { opacity: 1; }
                100% { opacity: 0; transform: translate(-50%, -50%) scale(0.95); }
            }
            @keyframes ss-shutter {
                0% { top: 0; opacity: 1; }
                100% { top: 100%; opacity: 0; }
            }

            /* ── Mouse Cursor Bubble ── */
            #cursor-bubble {
                position: fixed;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(99, 102, 241, 0.5) 0%, rgba(99, 102, 241, 0.15) 60%, transparent 70%);
                border: 2px solid rgba(99, 102, 241, 0.6);
                transform: translate(-50%, -50%);
                pointer-events: none;
                z-index: 10001;
                display: none;
                transition: left 0.08s ease-out, top 0.08s ease-out, opacity 0.3s ease;
                box-shadow: 0 0 16px rgba(99, 102, 241, 0.3);
            }
            #cursor-bubble.visible {
                display: block;
                animation: bubble-appear 0.3s ease-out forwards;
            }
            #cursor-bubble .trail {
                position: absolute;
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: rgba(99, 102, 241, 0.3);
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
            }
            @keyframes bubble-appear {
                0% { opacity: 0; transform: translate(-50%, -50%) scale(0.3); }
                100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            }
        </style>
    </head>
    <body>
        <div id="cursor-bubble"></div>
        <div id="screenshot-overlay">
            <div class="flash"></div>
            <div class="border-frame"></div>
            <div class="shutter-line"></div>
            <div class="badge"><span class="icon">📸</span> Captura tomada</div>
        </div>
        <script>
            const ssEl = document.getElementById('screenshot-overlay');
            const cursorBubble = document.getElementById('cursor-bubble');
            let hideTimer = null;
            let bubbleHideTimer = null;

            window.showClick = (x, y, type) => {
                type = type || 'click';
                // Create a click-point element at position
                const el = document.createElement('div');
                el.className = 'click-point ' + type;
                el.style.left = x + 'px';
                el.style.top = y + 'px';
                el.innerHTML = 
                    '<div class="dot"></div>' +
                    '<div class="ripple ripple-1"></div>' +
                    '<div class="ripple ripple-2"></div>' +
                    '<div class="ripple ripple-3"></div>' +
                    '<div class="coord-label">(' + x + ', ' + y + ')</div>';
                document.body.appendChild(el);
                setTimeout(function() { el.remove(); }, 1200);

                // Also show/move cursor bubble
                window.showCursorAt(x, y);
            };
            
            window.showScreenshot = () => {
                ssEl.classList.remove('active');
                void ssEl.offsetWidth;
                ssEl.classList.add('active');
                if (hideTimer) clearTimeout(hideTimer);
                hideTimer = setTimeout(function() { ssEl.classList.remove('active'); }, 900);
            };

            window.showCursorAt = (x, y) => {
                cursorBubble.style.left = x + 'px';
                cursorBubble.style.top = y + 'px';
                cursorBubble.classList.add('visible');
                if (bubbleHideTimer) clearTimeout(bubbleHideTimer);
                bubbleHideTimer = setTimeout(function() {
                    cursorBubble.classList.remove('visible');
                }, 3000);
            };

            window.hideCursor = () => {
                cursorBubble.classList.remove('visible');
            };
        </script>
    </body>
    </html>
    `);

    actionOverlayWindow.setIgnoreMouseEvents(true, { forward: true });
    actionOverlayWindow.setVisibleOnAllWorkspaces(true);
    actionOverlayWindow.hide();

    actionOverlayWindow.on('closed', () => {
        actionOverlayWindow = null;
    });
}

ipcMain.handle('set-window-opacity', (_, opacity) => {
    if (mainWindow) {
        mainWindow.setOpacity(Math.max(0.5, Math.min(1.0, opacity)));
    }
});

ipcMain.handle('show-click-indicator', async (_, x, y, type) => {
    try {
        if (!actionOverlayWindow || actionOverlayWindow.isDestroyed()) {
            createActionOverlayWindow();
            await new Promise(resolve => setTimeout(resolve, 200));
        }
        if (actionOverlayWindow && !actionOverlayWindow.isDestroyed()) {
            actionOverlayWindow.show();
            const safeType = String(type || 'click').replace(/[^a-z_]/g, '');
            await actionOverlayWindow.webContents.executeJavaScript(
                `window.showClick && window.showClick(${Number(x) || 0}, ${Number(y) || 0}, '${safeType}')`
            );
            setTimeout(() => {
                if (actionOverlayWindow && !actionOverlayWindow.isDestroyed()) {
                    actionOverlayWindow.hide();
                }
            }, 1500);
        }
    } catch (err) {
        console.error('[IPC] show-click-indicator error:', err.message);
    }
});

ipcMain.handle('show-screenshot-overlay', async () => {
    try {
        // Ocultar ventana principal para que no salga en la captura
        if (mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible()) {
            mainWindow.hide();
        }
        // Pequeña pausa para que el OS aplique el ocultamiento
        await new Promise(resolve => setTimeout(resolve, 80));

        if (!actionOverlayWindow || actionOverlayWindow.isDestroyed()) {
            createActionOverlayWindow();
            await new Promise(resolve => setTimeout(resolve, 200));
        }
        if (actionOverlayWindow && !actionOverlayWindow.isDestroyed()) {
            actionOverlayWindow.show();
            await actionOverlayWindow.webContents.executeJavaScript(`window.showScreenshot && window.showScreenshot()`);
            setTimeout(() => {
                if (actionOverlayWindow && !actionOverlayWindow.isDestroyed()) {
                    actionOverlayWindow.hide();
                }
                // Restaurar ventana principal después del overlay
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.show();
                }
            }, 1200);
        } else {
            // Si no hay overlay, restaurar la ventana
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.show();
            }
        }
    } catch (err) {
        console.error('[IPC] show-screenshot-overlay error:', err.message);
        // Siempre restaurar la ventana en caso de error
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.show();
        }
    }
});

ipcMain.handle('set-executing-mode', (_, active) => {
    if (mainWindow) {
        if (active) {
            mainWindow.hide();
        } else {
            mainWindow.show();
        }
    }
    setOverlayInteractionLocked(active);
});

ipcMain.handle('show-cursor-bubble', async (_, x, y) => {
    try {
        if (!actionOverlayWindow || actionOverlayWindow.isDestroyed()) {
            createActionOverlayWindow();
            await new Promise(resolve => setTimeout(resolve, 200));
        }
        if (actionOverlayWindow && !actionOverlayWindow.isDestroyed()) {
            actionOverlayWindow.show();
            await actionOverlayWindow.webContents.executeJavaScript(
                `window.showCursorAt && window.showCursorAt(${Number(x) || 0}, ${Number(y) || 0})`
            );
        }
    } catch (err) {
        console.error('[IPC] show-cursor-bubble error:', err.message);
    }
});

// ── App Lifecycle ────────────────────────────────────────────

app.whenReady().then(async () => {
    watchConfigFiles();

    // 1. Lanzar backend Python como proceso hijo
    console.log('[App] Iniciando backend...');
    const backendOk = await startBackend();
    if (backendOk) {
        console.log('[App] Backend listo');
    } else {
        console.warn('[App] Backend no confirmó arranque — la UI intentará reconectar');
    }

    // 2. Crear UI
    createMainWindow();
    createOverlayWindow();
    createActionOverlayWindow();  // Pre-crear overlay de acciones
    createTray();
    applyAppPreferences(appPreferences);

    // Global shortcuts
    globalShortcut.register('Alt+G', () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide();
            } else {
                mainWindow.show();
                mainWindow.focus();
            }
        }
    });

    globalShortcut.register('Alt+Shift+G', () => {
        toggleOverlay(!isOverlayMode);
    });

    // Kill switch — Ctrl+Shift+Esc ya es del OS Task Manager, usar Ctrl+Shift+Q
    globalShortcut.register('Ctrl+Shift+Q', () => {
        app.isQuitting = true;
        app.quit();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    clearTimeout(configReloadTimer);
    clearTimeout(overlayStateSaveTimer);
    unwatchConfigFiles();
    persistOverlayStateToDisk();
    globalShortcut.unregisterAll();
    stopBackend();
});

app.on('activate', () => {
    if (mainWindow === null) {
        createMainWindow();
    }
    if (overlayWindow === null) {
        createOverlayWindow();
    }
    if (mainWindow && !mainWindow.isVisible()) {
        mainWindow.show();
        mainWindow.focus();
    }
});
