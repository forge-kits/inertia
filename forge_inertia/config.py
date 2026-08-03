from dataclasses import dataclass


@dataclass
class InertiaConfig:
    root_view: str = "public/build/index.html"
    public_dir: str = "public"
    version: str = ""
    dev_mode: bool = False
    vite_dev_url: str = "http://localhost:5173"
    vite_entry: str = "src/main.ts"


_config = InertiaConfig()
