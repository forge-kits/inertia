from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from forgeapi.config import KitConfig

from forgeapi.foundation import Provider

from .config import _config
from .middleware import InertiaMiddleware


class InertiaProvider(Provider):
    def register(self) -> None:
        self.app.add_middleware(InertiaMiddleware)

    def boot(self) -> None:
        build = Path(_config.public_dir) / "build"

        if build.exists():
            from fastapi.staticfiles import StaticFiles
            self.app.mount(
                "/build",
                StaticFiles(directory=str(build)),
                name="inertia-assets",
            )

        # Vite manifest → deterministic version string for asset busting
        manifest = build / ".vite" / "manifest.json"
        if not manifest.exists():
            manifest = build / "manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            _config.version = str(hash(json.dumps(data, sort_keys=True)))
