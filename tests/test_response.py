import pytest
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

from forgeapi.inertia.response import Inertia
from forgeapi.inertia.middleware import InertiaMiddleware
from forgeapi.inertia.config import _config
from forgeapi.inertia.share import share


def make_app(component="Dashboard", props=None):
    _props = props or {}
    app = FastAPI()
    app.add_middleware(InertiaMiddleware)

    @app.get("/", response_class=Response)
    async def index(request: Request) -> Response:
        return Inertia(component, props=_props, request=request)

    return app


async def _get(app, path="/", headers=None, params=None):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(path, headers=headers or {}, params=params or {})


class TestInitialLoad:
    async def test_returns_html_in_dev_mode(self):
        _config["dev_mode"] = True
        app = make_app()
        resp = await _get(app)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert '<div id="app">' in resp.text

    async def test_dev_html_contains_vite_client(self):
        _config["dev_mode"] = True
        _config["vite_dev_url"] = "http://localhost:5173"
        app = make_app()
        resp = await _get(app)
        assert "/@vite/client" in resp.text
        assert "localhost:5173" in resp.text

    async def test_dev_html_contains_page_json(self):
        _config["dev_mode"] = True
        app = make_app("Home", {"title": "hello"})
        resp = await _get(app)
        assert 'data-page="app"' in resp.text
        assert "Home" in resp.text

    async def test_prod_html_embeds_page_json(self, tmp_path):
        html_file = tmp_path / "index.html"
        html_file.write_text("<html><body><div id='app'></div></body></html>")
        _config["dev_mode"] = False
        _config["root_view"] = str(html_file)
        app = make_app("Prod", {"x": 1})
        resp = await _get(app)
        assert resp.status_code == 200
        assert "Prod" in resp.text
        assert 'data-page="app"' in resp.text

    async def test_prod_html_file_not_found_raises(self):
        _config["dev_mode"] = False
        _config["root_view"] = "/nonexistent/path/index.html"
        app = make_app()
        with pytest.raises(FileNotFoundError):
            await _get(app)

    async def test_prod_html_cache_invalidates_on_path_change(self, tmp_path):
        f1 = tmp_path / "v1.html"
        f1.write_text("<html><body>v1</body></html>")
        _config["dev_mode"] = False
        _config["root_view"] = str(f1)
        app = make_app()
        resp1 = await _get(app)
        assert "v1" in resp1.text

        f2 = tmp_path / "v2.html"
        f2.write_text("<html><body>v2</body></html>")
        _config["root_view"] = str(f2)
        resp2 = await _get(app)
        assert "v2" in resp2.text


class TestInertiaRequest:
    async def test_returns_json_with_inertia_header(self):
        _config["dev_mode"] = True
        app = make_app("Dashboard", {"user": "alice"})
        resp = await _get(app, headers={"X-Inertia": "true"})
        assert resp.status_code == 200
        assert resp.headers.get("x-inertia") == "true"
        assert resp.headers.get("vary") == "X-Inertia"
        assert "application/json" in resp.headers["content-type"]

    async def test_json_contains_component_and_props(self):
        _config["dev_mode"] = True
        app = make_app("Dashboard", {"user": "alice"})
        resp = await _get(app, headers={"X-Inertia": "true"})
        data = resp.json()
        assert data["component"] == "Dashboard"
        assert data["props"]["user"] == "alice"

    async def test_url_includes_query_string(self):
        _config["dev_mode"] = True
        app = make_app()
        resp = await _get(app, params={"page": "2", "q": "test"}, headers={"X-Inertia": "true"})
        data = resp.json()
        assert "page=2" in data["url"]
        assert "q=test" in data["url"]

    async def test_url_is_full_url_not_just_path(self):
        _config["dev_mode"] = True
        app = make_app()
        resp = await _get(app, headers={"X-Inertia": "true"})
        data = resp.json()
        assert data["url"].startswith("http://")

    async def test_version_in_page_object(self):
        _config["dev_mode"] = True
        _config["version"] = "v42"
        app = make_app()
        # Must send matching X-Inertia-Version so middleware doesn't intercept with 409
        resp = await _get(app, headers={"X-Inertia": "true", "X-Inertia-Version": "v42"})
        data = resp.json()
        assert data["version"] == "v42"

    async def test_callable_props_evaluated(self):
        _config["dev_mode"] = True
        app = make_app("A", {"count": lambda: 42})
        resp = await _get(app, headers={"X-Inertia": "true"})
        data = resp.json()
        assert data["props"]["count"] == 42

    async def test_shared_props_merged(self):
        _config["dev_mode"] = True
        share("app_name", "MyApp")
        app = make_app("Page", {"page_prop": 1})
        resp = await _get(app, headers={"X-Inertia": "true"})
        data = resp.json()
        assert data["props"]["app_name"] == "MyApp"
        assert data["props"]["page_prop"] == 1

    async def test_page_props_override_shared(self):
        _config["dev_mode"] = True
        share("key", "from_share")
        app = make_app("Page", {"key": "from_props"})
        resp = await _get(app, headers={"X-Inertia": "true"})
        data = resp.json()
        assert data["props"]["key"] == "from_props"


class TestPartialReloads:
    async def test_filters_props_to_requested_keys(self):
        _config["dev_mode"] = True
        app = make_app("Dashboard", {"user": "alice", "stats": {"visits": 99}})
        resp = await _get(app, headers={
            "X-Inertia": "true",
            "X-Inertia-Partial-Component": "Dashboard",
            "X-Inertia-Partial-Data": "user",
        })
        data = resp.json()
        assert "user" in data["props"]
        assert "stats" not in data["props"]

    async def test_ignored_when_component_mismatch(self):
        _config["dev_mode"] = True
        app = make_app("Dashboard", {"user": "alice", "stats": {"visits": 99}})
        resp = await _get(app, headers={
            "X-Inertia": "true",
            "X-Inertia-Partial-Component": "OtherPage",
            "X-Inertia-Partial-Data": "user",
        })
        data = resp.json()
        assert "user" in data["props"]
        assert "stats" in data["props"]

    async def test_callable_not_called_when_excluded(self):
        _config["dev_mode"] = True
        called = []

        def expensive():
            called.append(1)
            return {"big": "data"}

        app = make_app("Dashboard", {"cheap": "val", "expensive": expensive})
        await _get(app, headers={
            "X-Inertia": "true",
            "X-Inertia-Partial-Component": "Dashboard",
            "X-Inertia-Partial-Data": "cheap",
        })
        assert called == []

    async def test_callable_called_when_included(self):
        _config["dev_mode"] = True
        called = []

        def expensive():
            called.append(1)
            return {"big": "data"}

        app = make_app("Dashboard", {"cheap": "val", "expensive": expensive})
        resp = await _get(app, headers={
            "X-Inertia": "true",
            "X-Inertia-Partial-Component": "Dashboard",
            "X-Inertia-Partial-Data": "expensive",
        })
        assert called == [1]
        data = resp.json()
        assert data["props"]["expensive"] == {"big": "data"}

    async def test_shared_callable_not_called_when_excluded(self):
        _config["dev_mode"] = True
        called = []

        share("cheap", "ok")
        share("expensive", lambda r: called.append(1) or "data")

        app = make_app("Dashboard")
        await _get(app, headers={
            "X-Inertia": "true",
            "X-Inertia-Partial-Component": "Dashboard",
            "X-Inertia-Partial-Data": "cheap",
        })
        assert called == []

    async def test_multiple_partial_keys(self):
        _config["dev_mode"] = True
        app = make_app("Page", {"a": 1, "b": 2, "c": 3})
        resp = await _get(app, headers={
            "X-Inertia": "true",
            "X-Inertia-Partial-Component": "Page",
            "X-Inertia-Partial-Data": "a,c",
        })
        data = resp.json()
        assert data["props"] == {"a": 1, "c": 3}
