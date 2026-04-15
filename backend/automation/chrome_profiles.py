"""
Chrome profile discovery and launch helpers for Windows.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class ChromeProfileExplorer:
    """Discover and open Chrome profiles without relying on UI heuristics."""

    def __init__(
        self,
        chrome_exe: Path | None = None,
        user_data_dir: Path | None = None,
    ) -> None:
        self._chrome_exe = chrome_exe
        self._user_data_dir = user_data_dir

    def find_chrome_exe(self) -> Path:
        if self._chrome_exe and self._chrome_exe.exists():
            return self._chrome_exe

        candidates = [
            Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                self._chrome_exe = candidate
                return candidate

        raise FileNotFoundError("No se encontro chrome.exe en rutas tipicas de Windows.")

    def chrome_user_data_dir(self) -> Path:
        if self._user_data_dir:
            return self._user_data_dir

        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise EnvironmentError("LOCALAPPDATA no esta definido.")

        self._user_data_dir = Path(local) / "Google" / "Chrome" / "User Data"
        return self._user_data_dir

    def load_local_state(self) -> dict[str, Any]:
        local_state_path = self.chrome_user_data_dir() / "Local State"
        if not local_state_path.exists():
            raise FileNotFoundError(f"No existe Local State: {local_state_path}")

        raw = local_state_path.read_text(encoding="utf-8", errors="replace")
        return json.loads(raw)

    def discover(self) -> list[dict[str, Any]]:
        user_data_dir = self.chrome_user_data_dir()
        state = self.load_local_state()

        profile_root = state.get("profile", {}) or {}
        info_cache = profile_root.get("info_cache", {}) or {}
        last_used = profile_root.get("last_used")

        profiles: list[dict[str, Any]] = []
        for dir_name, meta in info_cache.items():
            profile_path = user_data_dir / dir_name
            if not profile_path.exists():
                continue

            display_name = meta.get("shortcut_name") or meta.get("name") or dir_name
            email = meta.get("user_name") or meta.get("gaia_name") or ""

            profiles.append(
                {
                    "dir_name": dir_name,
                    "display_name": display_name,
                    "email": email,
                    "path": str(profile_path),
                    "last_used": dir_name == last_used,
                }
            )

        profiles.sort(key=lambda item: (not item["last_used"], item["display_name"].lower()))
        return profiles

    def select(self, query: str | None = None) -> dict[str, Any]:
        profiles = self.discover()
        if not profiles:
            raise RuntimeError("No encontre perfiles existentes de Chrome.")

        if query:
            normalized = query.strip().lower()
            exact: list[dict[str, Any]] = []
            partial: list[dict[str, Any]] = []

            for profile in profiles:
                display_name = str(profile["display_name"]).lower()
                email = str(profile["email"]).lower()
                dir_name = str(profile["dir_name"]).lower()
                haystack = " | ".join([display_name, email, dir_name])

                if normalized in {display_name, email, dir_name}:
                    exact.append(profile)
                elif normalized in haystack:
                    partial.append(profile)

            if exact:
                return exact[0]
            if partial:
                return partial[0]

        for profile in profiles:
            if profile["last_used"]:
                return profile

        for profile in profiles:
            if profile["dir_name"] == "Default":
                return profile

        return profiles[0]

    def open(
        self,
        query: str | None = None,
        url: str | None = None,
        new_window: bool = True,
    ) -> tuple[subprocess.Popen[Any], dict[str, Any]]:
        chrome = self.find_chrome_exe()
        profile = self.select(query)

        args = [
            str(chrome),
            f'--profile-directory={profile["dir_name"]}',
            "--ignore-profile-directory-if-not-exists",
        ]
        if new_window:
            args.append("--new-window")
        if url:
            args.append(url)

        process = subprocess.Popen(args)
        return process, profile

    def open_automation_profile(
        self,
        profile_name: str = "chrome-agent-profile",
        url: str | None = None,
        new_window: bool = True,
    ) -> tuple[subprocess.Popen[Any], Path]:
        chrome = self.find_chrome_exe()
        profile_root = Path.home() / profile_name
        profile_root.mkdir(parents=True, exist_ok=True)

        args = [
            str(chrome),
            f"--user-data-dir={profile_root}",
        ]
        if new_window:
            args.append("--new-window")
        if url:
            args.append(url)

        process = subprocess.Popen(args)
        return process, profile_root
