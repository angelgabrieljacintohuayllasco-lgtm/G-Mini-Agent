/**
 * G-Mini Agent Bridge — Popup Script
 */

const dot = document.getElementById("dot");
const statusText = document.getElementById("status-text");
const reconnectBtn = document.getElementById("reconnect-btn");

function updateUI(connected) {
  dot.className = "dot " + (connected ? "connected" : "disconnected");
  statusText.textContent = connected
    ? "Conectado al backend"
    : "Desconectado";
}

// Obtener estado actual del background
chrome.runtime.sendMessage({ type: "getStatus" }, (resp) => {
  if (resp) updateUI(resp.connected);
});

// Escuchar cambios de estado
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "status") {
    updateUI(msg.connected);
  }
});

// Botón reconectar
reconnectBtn.addEventListener("click", () => {
  statusText.textContent = "Reconectando...";
  chrome.runtime.sendMessage({ type: "reconnect" }, () => {
    setTimeout(() => {
      chrome.runtime.sendMessage({ type: "getStatus" }, (resp) => {
        if (resp) updateUI(resp.connected);
      });
    }, 2000);
  });
});
