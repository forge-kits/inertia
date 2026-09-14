# forge-inertia

[Inertia.js](https://inertiajs.com) adapter for [forge-kits](https://pypi.org/project/forge-kits/) / FastAPI.  
Brings the Laravel Inertia workflow to Python — same protocol, same mental model.

```
pip install forge-kits-inertia
```

---

## Requirements

- Python ≥ 3.11
- forge-kits ≥ 1.6.3
- A Vite + Vue 3 (or React/Svelte) frontend with `@inertiajs/vue3` (or equivalent)

---

## Setup

### 1. Register the provider

```python
# config/project.py
from forgeapi.inertia import InertiaProvider

config = {
    "providers": [InertiaProvider],
    ...
}
```

### 2. Create `config/inertia.py`

```python
# config/inertia.py
from forgeapi import env

config = {
    "dev_mode":     env("INERTIA_DEV", False),
    "vite_dev_url": env("VITE_DEV_URL", "http://localhost:5173"),
    # Optional overrides (shown with defaults):
    # "root_view":  "public/build/index.html",
    # "public_dir": "public",
    # "vite_entry": "src/main.ts",
    # "version":    "",   # auto-detected from Vite manifest when empty
}
```

### 3. Frontend entry (`src/main.ts`)

```ts
import { createApp, h } from 'vue'
import { createInertiaApp } from '@inertiajs/vue3'
import './style.css'

createInertiaApp({
  resolve: name => {
    const pages = import.meta.glob('./Pages/**/*.vue', { eager: true })
    return pages[`./Pages/${name}.vue`]
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el)
  },
})
```

### 4. Vite config (`vite.config.ts`)

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../public/build',
    emptyOutDir: true,
  },
})
```

---

## Returning an Inertia response

```python
from fastapi import Request
from fastapi.responses import Response
from forgeapi.controllers import Controller, route
from forgeapi.inertia import Inertia

class DashboardController(Controller):
    prefix = "/dashboard"

    @route.get("/", response_class=Response)
    async def index(self, request: Request) -> Response:
        return Inertia("Dashboard", props={"stats": await get_stats()}, request=request)
```

The component name maps directly to `Pages/Dashboard.vue` (or `.tsx`, `.svelte`).

### Lazy (callable) props

Props that are callables are only evaluated when actually needed — useful for partial reloads:

```python
return Inertia("Dashboard", props={
    "user":  current_user.dict(),       # always evaluated
    "stats": lambda: get_heavy_stats(), # skipped on partial reloads that don't request it
}, request=request)
```

---

## Shared data

Equivalent of Laravel's `HandleInertiaRequests` middleware — data shared on every response.

```python
# config/project.py (or a dedicated boot file)
from forgeapi.inertia import inertia_share

# Static value
inertia_share("app_name", "My App")

# Per-request callable — receives FastAPI Request
inertia_share("auth", lambda req: {
    "user": req.state.user.dict() if hasattr(req.state, "user") else None,
})
```

Shared props are merged with page props on every Inertia response. Page props override shared props on key collision.

---

## Partial reloads

forge-inertia handles `X-Inertia-Partial-Data` / `X-Inertia-Partial-Component` automatically:

- Props not in the requested set are excluded from the response.
- Shared prop callables not in the set are never called.
- Page prop callables (lambdas) not in the set are never called.
- If the component name doesn't match, all props are returned normally.

No controller changes required — the adapter filters at the response layer.

---

## Configuration reference

All options with their defaults:

| Key | Default | Description |
|---|---|---|
| `root_view` | `"public/build/index.html"` | Compiled HTML shell served on initial load |
| `public_dir` | `"public"` | Static assets root (mounted at `/build`) |
| `version` | `""` | Asset version; auto-set from Vite manifest when empty |
| `dev_mode` | `False` | `True` → serve from Vite dev server (full HMR, no build step) |
| `vite_dev_url` | `"http://localhost:5173"` | Vite dev server base URL |
| `vite_entry` | `"src/main.ts"` | Frontend entry point (injected in dev HTML shell) |

---

## Dev workflow

Two terminals:

```bash
# Frontend (in resources/)
npm run dev

# Backend (in project root)
forgeapi runserver --reload
```

Set `INERTIA_DEV=true` in `.env`. The backend serves an HTML shell that loads JS/CSS directly from the Vite dev server — full HMR, no build step.

## Production

```bash
# Build frontend
npm run build   # outputs to public/build/

# Run server
forgeapi runserver
```

`InertiaProvider` auto-mounts `/build` as static files and reads the Vite manifest to set the asset version hash (SHA-1, deterministic across restarts).

---

## Protocol compatibility

| Feature | Status |
|---|---|
| Initial page load (HTML shell) | ✅ |
| Subsequent navigation (XHR/JSON) | ✅ |
| Asset version mismatch → 409 + hard reload | ✅ |
| POST/PUT/PATCH/DELETE 302 → 303 redirect | ✅ |
| Shared props (per-request callables) | ✅ |
| Partial reloads (`X-Inertia-Partial-Data`) | ✅ |
| Lazy (callable) page props | ✅ |
| SSR | ❌ not yet |
