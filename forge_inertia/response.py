import json
from pathlib import Path

from fastapi import Request
from fastapi.responses import Response

from .config import _config
from .share import resolve_shared

_root_html: tuple[str, str] | None = None  # (resolved_path, content)


def _load_root_html() -> str:
    global _root_html
    path = str(Path(_config["root_view"]))
    if _root_html is None or _root_html[0] != path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Inertia root view not found: {p}\n"
                "Run `npm run build` or set root_view in config/inertia.py."
            )
        _root_html = (path, p.read_text(encoding="utf-8"))
    return _root_html[1]


def _render_html(page: dict) -> str:
    page_json = json.dumps(page)
    script_tag = f'<script type="application/json" data-page="app">{page_json}</script>'
    return _load_root_html().replace("</body>", f"{script_tag}\n</body>", 1)


def _dev_html(page: dict) -> str:
    page_json = json.dumps(page)
    base = _config["vite_dev_url"].rstrip("/")
    entry = _config["vite_entry"].lstrip("/")
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


def _resolve_props(props: dict, only: set[str] | None = None) -> dict:
    result = {}
    for k, v in props.items():
        if only is not None and k not in only:
            continue
        result[k] = v() if callable(v) else v
    return result


class InertiaResponse(Response):
    def __init__(self, request: Request, component: str, props: dict) -> None:
        # Partial reload: only return the requested subset of props
        only: set[str] | None = None
        partial_component = request.headers.get("X-Inertia-Partial-Component", "")
        partial_data = request.headers.get("X-Inertia-Partial-Data", "")
        if partial_component == component and partial_data:
            only = {k.strip() for k in partial_data.split(",") if k.strip()}

        page = {
            "component": component,
            "props": {
                **resolve_shared(request, only=only),
                **_resolve_props(props, only=only),
            },
            "url": str(request.url),
            "version": _config["version"],
        }

        if request.headers.get("X-Inertia"):
            super().__init__(
                content=json.dumps(page),
                media_type="application/json",
                headers={"X-Inertia": "true", "Vary": "X-Inertia"},
            )
        else:
            html = _dev_html(page) if _config["dev_mode"] else _render_html(page)
            super().__init__(content=html, media_type="text/html")


def Inertia(component: str, props: dict | None = None, *, request: Request) -> InertiaResponse:
    return InertiaResponse(request, component, props or {})
