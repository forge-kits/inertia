import pytest
import httpx
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse

from forgeapi.inertia.middleware import InertiaMiddleware
from forgeapi.inertia.config import _config


def make_app():
    app = FastAPI()
    app.add_middleware(InertiaMiddleware)

    @app.post("/form")
    async def form():
        return RedirectResponse(url="/success", status_code=302)

    @app.get("/page")
    async def page():
        return JSONResponse({"ok": True})

    return app


async def _request(app, method, path, headers=None, follow_redirects=True):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=follow_redirects,
    ) as client:
        return await getattr(client, method)(path, headers=headers or {})


class TestRedirectRewrite:
    async def test_post_302_becomes_303_with_inertia_header(self):
        app = make_app()
        resp = await _request(app, "post", "/form", {"X-Inertia": "true"}, follow_redirects=False)
        assert resp.status_code == 303

    async def test_post_302_unchanged_without_inertia_header(self):
        app = make_app()
        resp = await _request(app, "post", "/form", follow_redirects=False)
        assert resp.status_code == 302

    async def test_get_not_affected(self):
        app = make_app()
        resp = await _request(app, "get", "/page")
        assert resp.status_code == 200


class TestVersionMismatch:
    async def test_409_on_version_mismatch(self):
        _config["version"] = "abc123"
        app = make_app()
        resp = await _request(app, "get", "/page", {
            "X-Inertia": "true",
            "X-Inertia-Version": "wrong_version",
        })
        assert resp.status_code == 409
        assert resp.headers.get("x-inertia-location") == "http://test/page"

    async def test_no_409_when_version_matches(self):
        _config["version"] = "abc123"
        app = make_app()
        resp = await _request(app, "get", "/page", {
            "X-Inertia": "true",
            "X-Inertia-Version": "abc123",
        })
        assert resp.status_code == 200

    async def test_no_409_when_version_not_configured(self):
        _config["version"] = ""
        app = make_app()
        resp = await _request(app, "get", "/page", {
            "X-Inertia": "true",
            "X-Inertia-Version": "anything",
        })
        assert resp.status_code == 200

    async def test_no_409_on_non_inertia_request(self):
        _config["version"] = "abc123"
        app = make_app()
        resp = await _request(app, "get", "/page")
        assert resp.status_code == 200
