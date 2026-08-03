from dataclasses import dataclass


@dataclass
class InertiaConfig:
    root_view: str = "public/build/index.html"
    public_dir: str = "public"
    version: str = ""


_config = InertiaConfig()
