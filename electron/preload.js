/**
 * G-Mini Agent — Preload script.
 * Expone APIs seguras al renderer via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('gmini', {
    // Backend URL
    getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),

    // Window controls
    minimize: () => ipcRenderer.invoke('minimize-window'),
    close: () => ipcRenderer.invoke('close-window'),
    toggleAlwaysOnTop: (value) => ipcRenderer.invoke('toggle-always-on-top', value),
    getAppRuntimeSettings: () => ipcRenderer.invoke('get-app-runtime-settings'),
    reloadAppRuntimeSettings: () => ipcRenderer.invoke('reload-app-runtime-settings'),

    // Overlay
    toggleOverlay: (enable) => ipcRenderer.invoke('toggle-overlay', enable),
    setOverlayText: (text) => ipcRenderer.invoke('set-overlay-text', text),
    overlayGetState: () => ipcRenderer.invoke('overlay:get-state'),
    overlaySetInteractive: (interactive) => ipcRenderer.invoke('overlay:set-interactive', interactive),
    overlaySetCharacterRuntime: (payload) => ipcRenderer.invoke('overlay:set-character-runtime', payload),
    overlayMoveBy: (dx, dy) => ipcRenderer.invoke('overlay:move-by', dx, dy),
    overlayResizeBy: (delta, anchor) => ipcRenderer.invoke('overlay:resize-by', delta, anchor),
    overlaySetBounds: (bounds) => ipcRenderer.invoke('overlay:set-bounds', bounds),

    // Overlay receive
    onOverlayText: (callback) => {
        ipcRenderer.on('overlay-text', (_, text) => callback(text));
    },
    onOverlayState: (callback) => {
        ipcRenderer.on('overlay-state', (_, state) => callback(state));
    },
    onOverlayCharacterRuntime: (callback) => {
        ipcRenderer.on('overlay-character-runtime', (_, payload) => callback(payload));
    },

    // Window transparency & effects
    setWindowOpacity: (opacity) => ipcRenderer.invoke('set-window-opacity', opacity),
    showClickIndicator: (x, y, type) => ipcRenderer.invoke('show-click-indicator', x, y, type),
    showScreenshotOverlay: () => ipcRenderer.invoke('show-screenshot-overlay'),
    showCursorBubble: (x, y) => ipcRenderer.invoke('show-cursor-bubble', x, y),
    setExecutingMode: (active) => ipcRenderer.invoke('set-executing-mode', active),
});
