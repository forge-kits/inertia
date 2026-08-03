from typing import Any, Callable
from fastapi import Request

_shared: dict[str, Any | Callable] = {}


def share(key: str, value: Any | Callable) -> None:
    _shared[key] = value


def resolve_shared(request: Request) -> dict:
    result = {}
    for k, v in _shared.items():
        result[k] = v(request) if callable(v) else v
    return result
