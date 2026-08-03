import json
from pathlib import Path

from fastapi import Request
from fastapi.responses import Response

from .config import _config
from .share import resolve_shared

_root_html: str | None = None


def _load_root_html() -> str:
    global _root_html
    if _root_html is None:
        path = Path(_config.root_view)
        if not path.exists():
            raise FileNotFoundError(
                f"Inertia root view not found: {path}\n"
                "Run `npm run build` or set inertia_config.root_view to the correct path."
            )
        _root_html = path.read_text(encoding="utf-8")
    return _root_html


def _render_html(page: dict) -> str:
    page_json = json.dumps(page).replace("'", "&#39;")
    return _load_root_html().replace(
        '<div id="app">',
        f"<div id=\"app\" data-page='{page_json}'>",
        1,
    )


class InertiaResponse(Response):
    def __init__(self, request: Request, component: str, props: dict) -> None:
        page = {
            "component": component,
            "props": {**resolve_shared(request), **props},
            "url": str(request.url.path),
            "version": _config.version,
        }

        if request.headers.get("X-Inertia"):
            super().__init__(
                content=json.dumps(page),
                media_type="application/json",
                headers={"X-Inertia": "true", "Vary": "X-Inertia"},
            )
        else:
            super().__init__(content=_render_html(page), media_type="text/html")


def Inertia(component: str, props: dict | None = None, *, request: Request) -> InertiaResponse:
    return InertiaResponse(request, component, props or {})
