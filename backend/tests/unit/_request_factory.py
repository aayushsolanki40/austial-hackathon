"""Shared test helper -- builds a minimal Starlette ``Request`` for guard unit
tests that need to call ``can_activate(ExecutionContext(...))`` directly
without spinning up a full ASGI app. Not itself a ``*_spec.py`` test module.
"""

from __future__ import annotations

from starlette.requests import Request


def make_request(
    *,
    headers: dict[str, str] | None = None,
    path_params: dict[str, str] | None = None,
    method: str = "GET",
    path: str = "/test",
) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "path_params": path_params or {},
        "client": ("testclient", 1),
    }
    return Request(scope)
