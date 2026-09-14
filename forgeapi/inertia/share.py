from typing import Any, Callable
from fastapi import Request

_shared: dict[str, Any | Callable] = {}


def share(key: str, value: Any | Callable) -> None:
    _shared[key] = value


def resolve_shared(request: Request, *, only: set[str] | None = None) -> dict:
    result = {}
    for k, v in _shared.items():
        if only is not None and k not in only:
            continue
        result[k] = v(request) if callable(v) else v
    return result


def _reset_shared() -> None:
    _shared.clear()
