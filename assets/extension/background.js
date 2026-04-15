/**
 * G-Mini Agent Bridge — Background Service Worker
 *
 * Conecta con el backend G-Mini Agent via WebSocket y enruta comandos
 * al content script de la pestaña activa o a las chrome.* APIs.
 */

// ─── Estado global ──────────────────────────────────────────
let ws = null;
let reconnectTimer = null;
let keepAliveInterval = null;
let isConnected = false;
const BACKEND_URL = "ws://127.0.0.1:8765/ws/extension";
const RECONNECT_INTERVAL_MS = 3000;
const COMMAND_TIMEOUT_MS = 15000;
const KEEPALIVE_INTERVAL_MS = 20000; // Ping cada 20s para evitar suspension del SW
const pendingResponses = new Map(); // id → {resolve, reject, timer}

// ─── WebSocket Connection ───────────────────────────────────
function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    ws = new WebSocket(BACKEND_URL);
  } catch (err) {
    console.warn("[GMini Bridge] WS create failed:", err.message);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    console.log("[GMini Bridge] Connected to backend");
    isConnected = true;
    clearTimeout(reconnectTimer);

    // Iniciar keepalive para evitar suspension del service worker
    startKeepAlive();

    // Enviar handshake con info del perfil
    getProfileInfo().then((info) => {
      wsSend("ext:hello", info);
    });

    // Notificar popup
    broadcastStatus();
  };

  ws.onmessage = (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      console.warn("[GMini Bridge] Invalid JSON:", event.data);
      return;
    }
    handleBackendMessage(msg);
  };

  ws.onclose = () => {
    console.log("[GMini Bridge] Disconnected");
    isConnected = false;
    ws = null;
    stopKeepAlive();
    broadcastStatus();
    scheduleReconnect();
  };

  ws.onerror = (err) => {
    console.warn("[GMini Bridge] WS error:", err);
    // onclose will fire after this
  };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, RECONNECT_INTERVAL_MS);
}

// ─── Keepalive: evita que Chrome suspenda el service worker ──
// Chrome Manifest V3 suspende service workers tras ~30s de inactividad.
// Un intervalo de ping mantiene el WebSocket activo y el SW despierto.
function startKeepAlive() {
  stopKeepAlive();
  keepAliveInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      wsSend("ext:ping", { ts: Date.now() });
    }
  }, KEEPALIVE_INTERVAL_MS);

  // chrome.alarms es la forma oficial de mantener un SW activo
  // Dispara cada 25s (mínimo de Chrome es ~1min pero con periodInMinutes < 1 funciona como one-shot)
  chrome.alarms.create("gmini-keepalive", { periodInMinutes: 0.4 });
}

function stopKeepAlive() {
  if (keepAliveInterval) {
    clearInterval(keepAliveInterval);
    keepAliveInterval = null;
  }
  chrome.alarms.clear("gmini-keepalive").catch(() => {});
}

// Listener de alarma: mantiene el SW despierto y verifica conexión
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "gmini-keepalive") {
    if (!isConnected) {
      connect();
    }
  }
});

function wsSend(event, data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ event, data }));
  }
}

// ─── Profile Info ───────────────────────────────────────────
async function getProfileInfo() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const activeTab = tabs[0] || {};
  return {
    extensionId: chrome.runtime.id,
    tabUrl: activeTab.url || "",
    tabTitle: activeTab.title || "",
    userAgent: navigator.userAgent,
  };
}

// ─── Broadcast status to popup ──────────────────────────────
function broadcastStatus() {
  chrome.runtime.sendMessage({
    type: "status",
    connected: isConnected,
  }).catch(() => {}); // popup might not be open
}

// ─── Handle incoming messages from backend ──────────────────
function handleBackendMessage(msg) {
  const { event, data } = msg;

  if (event === "ext:command") {
    executeCommand(data);
  } else if (event === "ext:ping") {
    wsSend("ext:pong", { ts: Date.now() });
  }
}

// ─── Command Router ─────────────────────────────────────────
async function executeCommand(cmd) {
  const { id, command, params } = cmd;
  let result;

  try {
    switch (command) {
      // ── Navigation ──
      case "navigate":
        result = await cmdNavigate(params);
        break;
      case "go_back":
        result = await cmdGoBack();
        break;
      case "go_forward":
        result = await cmdGoForward();
        break;
      case "wait_load":
        result = await cmdWaitLoad(params);
        break;

      // ── DOM Interactions (via content script) ──
      case "click":
        result = await cmdContentScript("click", params);
        break;
      case "type":
        result = await cmdContentScript("type", params);
        break;
      case "fill":
        result = await cmdContentScript("fill", params);
        break;
      case "press":
        result = await cmdContentScript("press", params);
        break;
      case "scroll":
        result = await cmdContentScript("scroll", params);
        break;
      case "hover":
        result = await cmdContentScript("hover", params);
        break;
      case "select":
        result = await cmdContentScript("select", params);
        break;
      case "extract":
        result = await cmdContentScript("extract", params);
        break;
      case "get_dom":
        result = await cmdContentScript("get_dom", params);
        break;
      case "eval":
        result = await cmdContentScript("eval", params);
        break;
      case "wait_for":
        result = await cmdContentScript("wait_for", params);
        break;
      case "remove_overlays":
        result = await cmdContentScript("remove_overlays", params);
        break;

      // ── Page State ──
      case "snapshot":
        result = await cmdSnapshot();
        break;
      case "screenshot":
        result = await cmdScreenshot();
        break;
      case "page_info":
        result = await cmdPageInfo();
        break;

      // ── Tabs ──
      case "tabs_list":
        result = await cmdTabsList();
        break;
      case "tab_switch":
        result = await cmdTabSwitch(params);
        break;
      case "tab_new":
        result = await cmdTabNew(params);
        break;
      case "tab_close":
        result = await cmdTabClose(params);
        break;

      // ── Downloads ──
      case "downloads_list":
        result = await cmdDownloadsList(params);
        break;

      default:
        result = { success: false, error: `Unknown command: ${command}` };
    }
  } catch (err) {
    result = { success: false, error: err.message || String(err) };
  }

  // Enviar respuesta al backend
  wsSend("ext:response", { id, ...result });
}

// ─── Navigation Commands ────────────────────────────────────
async function cmdNavigate(params) {
  const tab = await getActiveTab();
  await chrome.tabs.update(tab.id, { url: params.url });

  // Esperar a que la pestaña termine de cargar
  await waitForTabLoad(tab.id, 30000);

  const updated = await chrome.tabs.get(tab.id);
  return { success: true, url: updated.url, title: updated.title };
}

async function cmdGoBack() {
  const tab = await getActiveTab();
  await chrome.tabs.goBack(tab.id);
  await sleep(500);
  const updated = await chrome.tabs.get(tab.id);
  return { success: true, url: updated.url, title: updated.title };
}

async function cmdGoForward() {
  const tab = await getActiveTab();
  await chrome.tabs.goForward(tab.id);
  await sleep(500);
  const updated = await chrome.tabs.get(tab.id);
  return { success: true, url: updated.url, title: updated.title };
}

async function cmdWaitLoad(params) {
  const tab = await getActiveTab();
  const timeout = params?.timeout_ms || 30000;
  await waitForTabLoad(tab.id, timeout);
  const updated = await chrome.tabs.get(tab.id);
  return { success: true, url: updated.url, title: updated.title, status: updated.status };
}

// ─── Content Script Commands ────────────────────────────────
async function cmdContentScript(action, params) {
  const tab = await getActiveTab();

  // Asegurar que el content script está inyectado
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
  } catch {
    // Content script ya inyectado o la página no lo permite
  }

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error(`Content script timeout for '${action}' after ${COMMAND_TIMEOUT_MS}ms`));
    }, COMMAND_TIMEOUT_MS);

    chrome.tabs.sendMessage(tab.id, { action, params }, (response) => {
      clearTimeout(timeout);
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response || { success: false, error: "No response from content script" });
      }
    });
  });
}

// ─── Page State Commands ────────────────────────────────────
async function cmdSnapshot() {
  const tab = await getActiveTab();

  // Obtener texto del body via content script
  let bodyText = "";
  try {
    const resp = await cmdContentScript("extract", { selector: "body" });
    bodyText = resp.text || "";
  } catch {
    bodyText = "[No se pudo extraer texto]";
  }

  return {
    success: true,
    url: tab.url,
    title: tab.title,
    text: bodyText.substring(0, 8000),
  };
}

async function cmdScreenshot() {
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
      format: "png",
      quality: 80,
    });
    // Quitar el prefijo data:image/png;base64,
    const base64 = dataUrl.replace(/^data:image\/\w+;base64,/, "");
    return { success: true, image_base64: base64 };
  } catch (err) {
    return { success: false, error: "Screenshot failed: " + err.message };
  }
}

async function cmdPageInfo() {
  const tab = await getActiveTab();
  let viewport = { width: 0, height: 0 };
  try {
    const resp = await cmdContentScript("eval", {
      script: "JSON.stringify({width: window.innerWidth, height: window.innerHeight})",
    });
    if (resp.success && resp.result) {
      viewport = JSON.parse(resp.result);
    }
  } catch {}

  return {
    success: true,
    url: tab.url,
    title: tab.title,
    viewport,
  };
}

// ─── Tab Commands ───────────────────────────────────────────
async function cmdTabsList() {
  const tabs = await chrome.tabs.query({ currentWindow: true });
  const items = tabs.map((t, i) => ({
    index: i,
    id: t.id,
    url: t.url,
    title: t.title,
    active: t.active,
  }));
  return { success: true, tabs: items };
}

async function cmdTabSwitch(params) {
  const tabs = await chrome.tabs.query({ currentWindow: true });
  const index = parseInt(params.index, 10);
  if (index < 0 || index >= tabs.length) {
    return { success: false, error: `Tab index ${index} out of range (0-${tabs.length - 1})` };
  }
  await chrome.tabs.update(tabs[index].id, { active: true });
  return { success: true, index, url: tabs[index].url, title: tabs[index].title };
}

async function cmdTabNew(params) {
  const tab = await chrome.tabs.create({ url: params?.url || "about:blank" });
  if (params?.url) {
    await waitForTabLoad(tab.id, 30000);
  }
  const updated = await chrome.tabs.get(tab.id);
  return { success: true, index: updated.index, url: updated.url, title: updated.title };
}

async function cmdTabClose(params) {
  const tabs = await chrome.tabs.query({ currentWindow: true });
  if (tabs.length <= 1) {
    return { success: false, error: "Cannot close the last tab" };
  }
  let tabId;
  if (params?.index !== undefined) {
    const index = parseInt(params.index, 10);
    if (index < 0 || index >= tabs.length) {
      return { success: false, error: `Tab index ${index} out of range` };
    }
    tabId = tabs[index].id;
  } else {
    const active = tabs.find((t) => t.active);
    tabId = active ? active.id : tabs[tabs.length - 1].id;
  }
  await chrome.tabs.remove(tabId);
  return { success: true };
}

// ─── Downloads ──────────────────────────────────────────────
async function cmdDownloadsList(params) {
  const limit = params?.limit || 20;
  const items = await chrome.downloads.search({
    limit,
    orderBy: ["-startTime"],
  });
  const downloads = items.map((d) => ({
    id: d.id,
    filename: d.filename,
    url: d.url,
    state: d.state,
    fileSize: d.fileSize,
    startTime: d.startTime,
    endTime: d.endTime,
    mime: d.mime,
  }));
  return { success: true, downloads };
}

// ─── Helpers ────────────────────────────────────────────────
async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs.length) {
    throw new Error("No active tab found");
  }
  return tabs[0];
}

function waitForTabLoad(tabId, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve(); // resolve anyway after timeout, don't block
    }, timeout);

    function listener(updatedTabId, changeInfo) {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);

    // Check if already loaded
    chrome.tabs.get(tabId).then((tab) => {
      if (tab.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    });
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Listeners from popup / content scripts ─────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "getStatus") {
    sendResponse({ connected: isConnected, backendUrl: BACKEND_URL });
    return false;
  }
  if (msg.type === "reconnect") {
    connect();
    sendResponse({ ok: true });
    return false;
  }
  // Forward responses from content script for tab messages
  return false;
});

// ─── Startup ────────────────────────────────────────────────
console.log("[GMini Bridge] Extension loaded, attempting connection...");
connect();
