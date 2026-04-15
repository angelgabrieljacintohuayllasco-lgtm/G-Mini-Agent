/**
 * G-Mini Agent Bridge — Content Script
 *
 * Inyectado en cada página. Ejecuta operaciones DOM enviadas desde el
 * background service worker: click, type, extract, scroll, etc.
 */

(() => {
  // Evitar doble inyección
  if (window.__gmini_bridge_injected) return;
  window.__gmini_bridge_injected = true;

  // ─── Message handler ────────────────────────────────────
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const { action, params } = msg;
    if (!action) return false;

    // Ejecutar acción async y enviar respuesta
    handleAction(action, params || {})
      .then(sendResponse)
      .catch((err) => sendResponse({ success: false, error: err.message || String(err) }));

    return true; // indica que sendResponse será llamado async
  });

  // ─── Action Dispatcher ──────────────────────────────────
  async function handleAction(action, params) {
    switch (action) {
      case "click":
        return doClick(params);
      case "type":
        return doType(params);
      case "fill":
        return doFill(params);
      case "press":
        return doPress(params);
      case "scroll":
        return doScroll(params);
      case "hover":
        return doHover(params);
      case "select":
        return doSelect(params);
      case "extract":
        return doExtract(params);
      case "get_dom":
        return doGetDom(params);
      case "eval":
        return doEval(params);
      case "wait_for":
        return doWaitFor(params);
      case "remove_overlays":
        return doRemoveOverlays();
      default:
        return { success: false, error: `Unknown content action: ${action}` };
    }
  }

  // ─── DOM Operations ─────────────────────────────────────

  function querySelector(selector) {
    // Intentar multiples selectores separados por coma
    const selectors = selector.split(",").map((s) => s.trim());
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el) return el;
      } catch {
        // selector inválido, probar siguiente
      }
    }
    return null;
  }

  async function doClick(params) {
    const { selector, force } = params;
    const el = querySelector(selector);
    if (!el) {
      return { success: false, error: `Element not found: ${selector}` };
    }

    // Scroll into view
    el.scrollIntoView({ behavior: "instant", block: "center" });
    await sleep(100);

    if (force) {
      // Click sintético — ignora overlays
      el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    } else {
      el.click();
    }

    return { success: true, tag: el.tagName, text: (el.textContent || "").substring(0, 100) };
  }

  async function doType(params) {
    const { selector, text, clear } = params;
    const el = querySelector(selector);
    if (!el) {
      return { success: false, error: `Element not found: ${selector}` };
    }

    el.focus();
    await sleep(50);

    if (clear !== false) {
      el.value = "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }

    // Simular escritura carácter por carácter (más natural)
    for (const char of text) {
      el.value += char;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new KeyboardEvent("keydown", { key: char, bubbles: true }));
      el.dispatchEvent(new KeyboardEvent("keyup", { key: char, bubbles: true }));
      await sleep(15 + Math.random() * 25); // entre 15-40ms por tecla
    }

    el.dispatchEvent(new Event("change", { bubbles: true }));
    return { success: true, typed: text.length };
  }

  async function doFill(params) {
    const { selector, text } = params;
    const el = querySelector(selector);
    if (!el) {
      return { success: false, error: `Element not found: ${selector}` };
    }

    el.focus();
    await sleep(50);

    // Set value directamente con setter nativo para React/Angular
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value"
    )?.set || Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      "value"
    )?.set;

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(el, text);
    } else {
      el.value = text;
    }

    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));

    return { success: true, filled: text.length };
  }

  async function doPress(params) {
    const { key } = params;
    const keyMap = {
      enter: "Enter",
      tab: "Tab",
      escape: "Escape",
      backspace: "Backspace",
      space: " ",
      arrowdown: "ArrowDown",
      arrowup: "ArrowUp",
      arrowleft: "ArrowLeft",
      arrowright: "ArrowRight",
      delete: "Delete",
      home: "Home",
      end: "End",
      pageup: "PageUp",
      pagedown: "PageDown",
    };

    const resolvedKey = keyMap[key.toLowerCase()] || key;
    const target = document.activeElement || document.body;

    target.dispatchEvent(
      new KeyboardEvent("keydown", { key: resolvedKey, code: resolvedKey, bubbles: true })
    );
    target.dispatchEvent(
      new KeyboardEvent("keypress", { key: resolvedKey, code: resolvedKey, bubbles: true })
    );
    target.dispatchEvent(
      new KeyboardEvent("keyup", { key: resolvedKey, code: resolvedKey, bubbles: true })
    );

    // Para Enter en formularios
    if (resolvedKey === "Enter" && target.form) {
      target.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    }

    return { success: true, key: resolvedKey };
  }

  async function doScroll(params) {
    const { direction, amount } = params;
    const px = (amount || 3) * 300;
    const dirMap = {
      down: [0, px],
      up: [0, -px],
      left: [-px, 0],
      right: [px, 0],
    };
    const [x, y] = dirMap[direction] || [0, px];
    window.scrollBy({ left: x, top: y, behavior: "smooth" });
    await sleep(400);
    return { success: true, scrollX: window.scrollX, scrollY: window.scrollY };
  }

  async function doHover(params) {
    const { selector } = params;
    const el = querySelector(selector);
    if (!el) {
      return { success: false, error: `Element not found: ${selector}` };
    }

    el.scrollIntoView({ behavior: "instant", block: "center" });
    await sleep(100);

    el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true, view: window }));
    el.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, view: window }));

    return { success: true, tag: el.tagName };
  }

  async function doSelect(params) {
    const { selector, value } = params;
    const el = querySelector(selector);
    if (!el || el.tagName !== "SELECT") {
      return { success: false, error: `Select element not found: ${selector}` };
    }

    el.value = value;
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return { success: true, selectedValue: el.value };
  }

  async function doExtract(params) {
    const { selector } = params;
    const sel = selector || "body";
    const el = querySelector(sel);
    if (!el) {
      return { success: false, error: `Element not found: ${sel}` };
    }

    const text = el.innerText || el.textContent || "";
    return { success: true, text: text.substring(0, 8000) };
  }

  async function doGetDom(params) {
    const { selector, max_depth, max_length } = params;
    const sel = selector || "body";
    const el = querySelector(sel);
    if (!el) {
      return { success: false, error: `Element not found: ${sel}` };
    }
    const depth = max_depth || 6;
    const limit = max_length || 12000;

    function serialize(node, d) {
      if (d > depth) return "";
      if (node.nodeType === Node.TEXT_NODE) {
        const t = (node.textContent || "").trim();
        return t ? t.substring(0, 200) : "";
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return "";
      const tag = node.tagName.toLowerCase();
      const skip = ["script", "style", "noscript", "svg", "path"];
      if (skip.includes(tag)) return "";
      let attrs = "";
      for (const a of ["id", "class", "href", "src", "type", "name", "role", "aria-label", "placeholder", "value"]) {
        const v = node.getAttribute(a);
        if (v) attrs += ` ${a}="${v.substring(0, 80)}"`;
      }
      let inner = "";
      for (const child of node.childNodes) {
        inner += serialize(child, d + 1);
        if (inner.length > limit) break;
      }
      return `<${tag}${attrs}>${inner}</${tag}>`;
    }

    const html = serialize(el, 0).substring(0, limit);
    return { success: true, html };
  }

  async function doEval(params) {
    const { script } = params;
    try {
      const result = await new Function(`return (async () => { ${script} })()`)();
      return { success: true, result: result !== undefined ? String(result) : null };
    } catch (err) {
      return { success: false, error: `Eval error: ${err.message}` };
    }
  }

  async function doWaitFor(params) {
    const { selector, timeout_ms, state } = params;
    const timeout = timeout_ms || 15000;
    const start = Date.now();

    while (Date.now() - start < timeout) {
      const el = querySelector(selector);
      if (el) {
        if (state === "hidden") {
          if (el.offsetParent === null || getComputedStyle(el).display === "none") {
            return { success: true, found: true, waited_ms: Date.now() - start };
          }
        } else {
          // default: "visible"
          if (el.offsetParent !== null && getComputedStyle(el).display !== "none") {
            return { success: true, found: true, waited_ms: Date.now() - start };
          }
        }
      }
      await sleep(200);
    }

    return { success: false, error: `Timeout waiting for '${selector}' (${timeout}ms)` };
  }

  async function doRemoveOverlays() {
    let removed = 0;
    const selectors = [
      // Overlays comunes
      '[class*="modal"]',
      '[class*="overlay"]',
      '[class*="popup"]',
      '[class*="dialog"]',
      '[class*="cookie"]',
      '[class*="consent"]',
      '[class*="backdrop"]',
      '[id*="modal"]',
      '[id*="overlay"]',
      '[id*="popup"]',
      '[id*="cookie"]',
    ];

    // Remover elementos con position fixed/sticky que cubren la pantalla
    document.querySelectorAll("*").forEach((el) => {
      const style = getComputedStyle(el);
      if (
        (style.position === "fixed" || style.position === "sticky") &&
        parseFloat(style.zIndex) > 999 &&
        el.tagName !== "HEADER" &&
        el.tagName !== "NAV"
      ) {
        el.remove();
        removed++;
      }
    });

    // Remover por selectores conocidos
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => {
        const style = getComputedStyle(el);
        if (
          style.position === "fixed" ||
          style.position === "absolute" ||
          parseFloat(style.zIndex) > 100
        ) {
          el.remove();
          removed++;
        }
      });
    }

    // Restaurar scroll si fue bloqueado
    document.body.style.overflow = "";
    document.documentElement.style.overflow = "";

    return { success: true, removed_elements: removed };
  }

  // ─── Helpers ────────────────────────────────────────────
  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }
})();
