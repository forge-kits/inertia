from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from forgeapi.config import KitConfig

from forgeapi.foundation import Provider

from .config import _config, _DEFAULTS
from .middleware import InertiaMiddleware


class InertiaProvider(Provider):
    def register(self) -> None:
        self.app.add_middleware(InertiaMiddleware)

        # Apply config/inertia.py section (forge-kits custom section pattern)
        section = self.config.get("inertia") or {}
        if isinstance(section, dict):
            _config.update({k: v for k, v in section.items() if k in _DEFAULTS})

    def boot(self) -> None:
        build = Path(_config["public_dir"]) / "build"

        if build.exists():
            from fastapi.staticfiles import StaticFiles
            self.app.mount(
                "/build",
                StaticFiles(directory=str(build)),
                name="inertia-assets",
            )

        # Vite manifest → deterministic asset version for cache busting
        # Only auto-set if not provided in config/inertia.py
        if not _config["version"]:
            manifest = build / ".vite" / "manifest.json"
            if not manifest.exists():
                manifest = build / "manifest.json"
            if manifest.exists():
                _config["version"] = hashlib.sha1(manifest.read_bytes()).hexdigest()[:16]
