"""
G-Mini Agent — browser-use Bridge.
Wrapper delgado sobre la librería browser-use (>=0.12) para perfiles de automatización.
Expone la misma interfaz que ExtensionBridge / BrowserController legacy.

browser-use 0.12+ usa CDP (Chrome DevTools Protocol) internamente.
Browser es alias de BrowserSession. Page y Element son clases propias de browser-use
(browser_use.actor.page.Page, browser_use.actor.element.Element).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger

# Lazy import: browser-use puede no estar instalado
_BrowserUse = None


def _ensure_browser_use():
    global _BrowserUse
    if _BrowserUse is not None:
        return True
    try:
        from browser_use import Browser as _B
        _BrowserUse = _B
        return True
    except ImportError:
        logger.warning("[BrowserUseBridge] browser-use no instalado (pip install browser-use)")
        return False


class BrowserUseBridge:
    """
    Backend de automatización para perfiles limpios usando browser-use.
    Para uso con browser_use_automation_profile() — NO para perfiles humanos.
    """

    def __init__(self):
        self._browser = None  # browser_use.Browser instance
        self._available = False
        self._profile_name: str = ""
        self._downloads_dir: Path | None = None

    async def initialize(self) -> None:
        self._available = _ensure_browser_use()
        if self._available:
            logger.info("[BrowserUseBridge] browser-use disponible")
        else:
            logger.warning("[BrowserUseBridge] browser-use NO disponible")

    def is_available(self) -> bool:
        return self._available

    async def ensure_automation_profile(
        self,
        profile_name: str = "chrome-agent-profile",
        headless: bool = False,
        prohibited_domains: list[str] | None = None,
        extra_args: list[str] | None = None,
        downloads_path: str | None = None,
    ) -> dict:
        """Crea un perfil limpio de automatización con browser-use."""
        if not self._available or not _BrowserUse:
            raise RuntimeError("browser-use no está instalado")

        await self.shutdown()

        user_data = Path.home() / ".g-mini-agent" / "profiles" / profile_name
        user_data.mkdir(parents=True, exist_ok=True)
        self._profile_name = profile_name

        dl_path = downloads_path or str(
            Path.home() / "Downloads" / "G-Mini-Agent"
        )
        self._downloads_dir = Path(dl_path)
        self._downloads_dir.mkdir(parents=True, exist_ok=True)

        kwargs: dict[str, Any] = {
            "headless": headless,
            "user_data_dir": str(user_data),
            "channel": "chrome",
            "keep_alive": True,
            "accept_downloads": True,
            "downloads_path": dl_path,
            "highlight_elements": True,
            "enable_default_extensions": True,
        }

        if prohibited_domains:
            kwargs["prohibited_domains"] = prohibited_domains

        if extra_args:
            kwargs["args"] = extra_args

        try:
            self._browser = _BrowserUse(**kwargs)

            # browser-use 0.12+: start() retorna None, el browser queda listo
            # para usar via get_current_page(), navigate_to(), etc.
            await self._browser.start()

            logger.info(f"[BrowserUseBridge] Perfil '{profile_name}' creado OK")
            return {
                "mode": "automation",
                "profile_ref": profile_name,
                "backend": "browser_use",
                "user_data_dir": str(user_data),
            }

        except Exception as e:
            logger.error(f"[BrowserUseBridge] Error creando perfil: {e}")
            self._browser = None
            raise

    async def shutdown(self) -> None:
        """Cierra el browser."""
        if self._browser:
            try:
                await self._browser.stop()
            except Exception as e:
                logger.warning(f"[BrowserUseBridge] Error cerrando browser: {e}")
            self._browser = None

    def _require_browser(self):
        if self._browser is None:
            raise RuntimeError("Browser-use: no hay sesión activa. Usa ensure_automation_profile() primero.")
        return self._browser

    async def _get_page(self):
        """Obtiene la página actual del browser. Crea una si no existe."""
        browser = self._require_browser()
        page = await browser.get_current_page()
        if page is None:
            page = await browser.new_page()
        return page

    async def _find_element(self, selector: str):
        """Busca un elemento por selector CSS. Lanza error si no existe."""
        page = await self._get_page()
        elements = await page.get_elements_by_css_selector(selector)
        if not elements:
            raise RuntimeError(f"Elemento no encontrado: {selector}")
        return elements[0]

    # ── Navegación ───────────────────────────────────────────

    async def navigate(self, url: str) -> dict:
        browser = self._require_browser()
        await browser.navigate_to(url)
        return {
            "url": await browser.get_current_page_url(),
            "title": await browser.get_current_page_title(),
        }

    async def go_back(self) -> dict:
        page = await self._get_page()
        await page.go_back()
        browser = self._require_browser()
        return {
            "url": await browser.get_current_page_url(),
            "title": await browser.get_current_page_title(),
        }

    async def go_forward(self) -> dict:
        page = await self._get_page()
        await page.go_forward()
        browser = self._require_browser()
        return {
            "url": await browser.get_current_page_url(),
            "title": await browser.get_current_page_title(),
        }

    async def wait_for_load(self, state: str = "domcontentloaded", timeout_ms: int = 30000) -> dict:
        browser = self._require_browser()
        # browser-use usa CDP, no tiene wait_for_load_state directo.
        # Esperar un breve periodo para que la página se estabilice.
        await asyncio.sleep(min(timeout_ms / 1000, 2.0))
        return {
            "url": await browser.get_current_page_url(),
            "title": await browser.get_current_page_title(),
        }

    # ── Interacción ──────────────────────────────────────────

    async def click(self, selector: str, force: bool = False, timeout_ms: int = 10000) -> dict:
        el = await self._find_element(selector)
        await el.click()
        return {"clicked": selector}

    async def type(self, selector: str, text: str, clear: bool = True, timeout_ms: int = 10000) -> dict:
        el = await self._find_element(selector)
        await el.fill(text, clear=clear)
        return {"typed": len(text), "selector": selector}

    async def fill(self, selector: str, text: str, timeout_ms: int = 10000) -> dict:
        el = await self._find_element(selector)
        await el.fill(text, clear=True)
        return {"filled": len(text), "selector": selector}

    async def press(self, key: str) -> dict:
        page = await self._get_page()
        await page.press(key)
        return {"key": key}

    async def scroll(self, direction: str = "down", amount: int = 3) -> dict:
        page = await self._get_page()
        delta_map = {"down": (0, 300), "up": (0, -300), "left": (-300, 0), "right": (300, 0)}
        dx, dy = delta_map.get(direction, (0, 300))
        await page.evaluate(
            f"() => window.scrollBy({{ left: {dx * amount}, top: {dy * amount}, behavior: 'smooth' }})"
        )
        await asyncio.sleep(0.4)
        return {"direction": direction, "amount": amount}

    async def hover(self, selector: str, timeout_ms: int = 10000) -> dict:
        el = await self._find_element(selector)
        await el.hover()
        return {"hovered": selector}

    async def select_option(self, selector: str, value: str, timeout_ms: int = 10000) -> dict:
        el = await self._find_element(selector)
        await el.select_option(value)
        return {"selected": value}

    async def wait_for_selector(self, selector: str, timeout_ms: int = 15000, state: str = "visible") -> dict:
        page = await self._get_page()
        deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000)
        while asyncio.get_event_loop().time() < deadline:
            elements = await page.get_elements_by_css_selector(selector)
            if elements:
                return {"found": True, "selector": selector}
            await asyncio.sleep(0.3)
        raise TimeoutError(f"Timeout esperando selector '{selector}' ({timeout_ms}ms)")

    async def remove_overlays(self) -> dict:
        page = await self._get_page()
        result = await page.evaluate("""() => {
            let c = 0;
            document.querySelectorAll('*').forEach(el => {
                const s = getComputedStyle(el);
                if ((s.position === 'fixed' || s.position === 'sticky') &&
                    parseFloat(s.zIndex) > 999 &&
                    el.tagName !== 'HEADER' && el.tagName !== 'NAV') {
                    el.remove(); c++;
                }
            });
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
            return c;
        }""")
        return {"removed_elements": int(result) if result else 0}

    # ── Lectura ──────────────────────────────────────────────

    async def extract(self, selector: str = "body", timeout_ms: int = 10000) -> dict:
        page = await self._get_page()
        sel_escaped = selector.replace("'", "\\'")
        text = await page.evaluate(
            f"() => {{ const el = document.querySelector('{sel_escaped}'); return el ? (el.innerText || el.textContent || '') : ''; }}"
        )
        return {"text": (text or "")[:8000]}

    async def snapshot(self) -> dict:
        browser = self._require_browser()
        url = await browser.get_current_page_url()
        title = await browser.get_current_page_title()
        try:
            state_text = await browser.get_state_as_text()
            body = state_text[:8000] if state_text else ""
        except Exception:
            body = ""
        return {"url": url, "title": title, "text": body}

    async def evaluate(self, script: str) -> dict:
        page = await self._get_page()
        # browser-use 0.12 requiere formato (...args) => para evaluate.
        # Si el script no empieza con ( o function, envolverlo.
        if not script.strip().startswith("(") and not script.strip().startswith("function"):
            script = f"() => {{ {script} }}"
        result = await page.evaluate(script)
        return {"result": result}

    async def screenshot(self) -> dict:
        page = await self._get_page()
        # browser-use 0.12: screenshot() retorna base64 string directamente
        image_b64 = await page.screenshot()
        return {"image_base64": image_b64}

    async def get_page_info(self) -> dict:
        browser = self._require_browser()
        return {
            "url": await browser.get_current_page_url(),
            "title": await browser.get_current_page_title(),
            "viewport": {"width": 0, "height": 0},
        }

    # ── Pestañas ─────────────────────────────────────────────

    async def list_tabs(self) -> dict:
        browser = self._require_browser()
        try:
            pages = await browser.get_pages()
        except Exception:
            return {"tabs": []}
        current = await browser.get_current_page()
        tabs = []
        for i, p in enumerate(pages):
            try:
                url = await p.get_url()
                title = await p.get_title()
            except Exception:
                url = ""
                title = ""
            tabs.append({
                "index": i,
                "url": url,
                "title": title,
                "active": p == current,
            })
        return {"tabs": tabs}

    async def switch_tab(self, index: int) -> dict:
        browser = self._require_browser()
        pages = await browser.get_pages()
        if index < 0 or index >= len(pages):
            raise IndexError(f"Tab {index} fuera de rango (0-{len(pages) - 1})")
        # Navegar a la página por índice (browser-use gestiona el tab activo)
        target = pages[index]
        url = await target.get_url()
        title = await target.get_title()
        return {"index": index, "url": url, "title": title}

    async def close_tab(self, index: int | None = None) -> dict:
        browser = self._require_browser()
        await browser.close_page()
        return {"closed": True}

    async def new_tab(self, url: str | None = None) -> dict:
        browser = self._require_browser()
        page = await browser.new_page(url)
        return {
            "url": await page.get_url() if url else "about:blank",
            "title": await page.get_title() if url else "",
        }

    # ── Descargas ────────────────────────────────────────────

    async def click_and_wait_for_download(
        self, selector: str, timeout_ms: int = 30000
    ) -> dict:
        # browser-use 0.12: las descargas se manejan automáticamente via downloads_path
        el = await self._find_element(selector)
        await el.click()
        # Esperar un momento para que la descarga inicie
        await asyncio.sleep(2.0)
        # Buscar la descarga más reciente en la carpeta
        recent = await self.list_downloads(limit=1)
        if recent:
            return recent[0]
        return {"filename": "unknown", "url": ""}

    async def list_downloads(self, limit: int = 20) -> list[dict]:
        """Lista archivos recientes en la carpeta de descargas."""
        if not self._downloads_dir or not self._downloads_dir.exists():
            return []
        files = sorted(self._downloads_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        return [
            {"name": f.name, "size_bytes": f.stat().st_size, "path": str(f)}
            for f in files[:limit]
            if f.is_file()
        ]

    async def check_downloads_folder(
        self,
        expected_ext: str | None = None,
        filename_contains: str | None = None,
        recency_seconds: int = 300,
        limit: int = 10,
    ) -> dict:
        """Busca descargas recientes que coincidan con los criterios."""
        import time

        dirs_to_check = []
        if self._downloads_dir:
            dirs_to_check.append(self._downloads_dir)
        default_dl = Path.home() / "Downloads"
        if default_dl.exists() and default_dl not in dirs_to_check:
            dirs_to_check.append(default_dl)

        now = time.time()
        found_files = []

        for dl_dir in dirs_to_check:
            if not dl_dir.exists():
                continue
            for f in dl_dir.iterdir():
                if not f.is_file():
                    continue
                if now - f.stat().st_mtime > recency_seconds:
                    continue
                if expected_ext and not f.suffix.lower() == expected_ext.lower():
                    continue
                if filename_contains and filename_contains.lower() not in f.name.lower():
                    continue
                found_files.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                    "age_seconds": int(now - f.stat().st_mtime),
                })
                if len(found_files) >= limit:
                    break

        found_files.sort(key=lambda x: x["age_seconds"])
        return {"found": len(found_files) > 0, "files": found_files}

    async def current_state(self) -> dict:
        """Estado actual del browser-use bridge."""
        active = self._browser is not None
        result: dict[str, Any] = {
            "mode": "automation",
            "backend": "browser_use",
            "profile_ref": self._profile_name,
            "active": active,
        }
        if active and self._browser:
            try:
                result["url"] = await self._browser.get_current_page_url()
                result["title"] = await self._browser.get_current_page_title()
            except Exception:
                pass
        return result
