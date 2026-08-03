# forge-inertia

[Inertia.js](https://inertiajs.com) adapter for [forge-kits](https://pypi.org/project/forge-kits/) / FastAPI.  
Brings the Laravel Inertia workflow to Python — same protocol, same mental model.

```
pip install forge-kits-inertia
```

---

## Requirements

- Python ≥ 3.11
- forge-kits ≥ 1.5.1
- A Vite + Vue 3 (or React/Svelte) frontend with `@inertiajs/vue3` (or equivalent)

---

## Setup

### 1. Register the provider

```python
# config/project.py
from forge_inertia import InertiaProvider, inertia_config

inertia_config.dev_mode     = env("INERTIA_DEV", False)
inertia_config.vite_dev_url = env("VITE_DEV_URL", "http://localhost:5173")

config = {
    "providers": [InertiaProvider],
    ...
}
```

### 2. Frontend entry (`src/main.ts`)

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

### 3. Vite config (`vite.config.ts`)

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import inertia from '@inertiajs/vite'

export default defineConfig({
  plugins: [vue(), inertia()],
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
from forge_inertia import Inertia

class DashboardController(Controller):
    prefix = "/dashboard"

    @route.get("/", response_class=Response)
    async def index(self, request: Request) -> Response:
        return Inertia("Dashboard", props={"stats": await get_stats()}, request=request)
```

The component name maps directly to `Pages/Dashboard.vue` (or `.tsx`, `.svelte`).

---

## Shared data

Equivalent of Laravel's `HandleInertiaRequests` middleware — data shared on every response.

```python
# config/project.py  (or a dedicated boot file)
from forge_inertia import inertia_share

# Static value
inertia_share("app_name", "My App")

# Per-request callable — receives FastAPI Request
inertia_share("auth", lambda req: {
    "user": req.state.user.dict() if hasattr(req.state, "user") else None,
})
```

Shared props are merged with page props on every Inertia response, just like Laravel.

---

## Configuration

All options with their defaults:

```python
from forge_inertia import inertia_config

inertia_config.root_view    = "public/build/index.html"  # compiled HTML shell
inertia_config.public_dir   = "public"                   # static assets root
inertia_config.version      = ""                         # auto-set from Vite manifest
inertia_config.dev_mode     = False                      # True → serve from Vite dev server
inertia_config.vite_dev_url = "http://localhost:5173"
inertia_config.vite_entry   = "src/main.ts"
```

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

`InertiaProvider` auto-mounts `/build` as static files and reads the Vite manifest to set the asset version hash.

---

## Protocol compatibility

forge-inertia implements the full [Inertia.js protocol](https://inertiajs.com/the-protocol):

| Feature | Status |
|---|---|
| Initial page load (HTML shell) | ✅ |
| Subsequent navigation (XHR/JSON) | ✅ |
| Asset version mismatch → 409 + hard reload | ✅ |
| POST/PUT/PATCH/DELETE 302 → 303 redirect | ✅ |
| Shared props (per-request callables) | ✅ |
| SSR | ❌ not yet |

---
