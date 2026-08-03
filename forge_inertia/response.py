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
    page_json = json.dumps(page)
    script_tag = f'<script type="application/json" data-page="app">{page_json}</script>'
    return _load_root_html().replace("</body>", f"{script_tag}\n</body>", 1)


def _dev_html(page: dict) -> str:
    page_json = json.dumps(page)
    base = _config.vite_dev_url.rstrip("/")
    entry = _config.vite_entry.lstrip("/")
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "  <head>\n"
        "    <meta charset=\"UTF-8\" />\n"
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
        "    <title>App</title>\n"
        "  </head>\n"
        "  <body>\n"
        "    <div id=\"app\"></div>\n"
        f"    <script type=\"application/json\" data-page=\"app\">{page_json}</script>\n"
        f"    <script type=\"module\" src=\"{base}/@vite/client\"></script>\n"
        f"    <script type=\"module\" src=\"{base}/{entry}\"></script>\n"
        "  </body>\n"
        "</html>"
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
            html = _dev_html(page) if _config.dev_mode else _render_html(page)
            super().__init__(content=html, media_type="text/html")


def Inertia(component: str, props: dict | None = None, *, request: Request) -> InertiaResponse:
    return InertiaResponse(request, component, props or {})
