"""FastAPI dependency-injection helpers.

Each router consumes these via ``Depends(...)`` so tests can override them
via ``app.dependency_overrides`` for TestClient-based coverage.
"""

from __future__ import annotations

from evidentia_core.catalogs.registry import FrameworkRegistry
from fastapi import Request


def get_registry() -> FrameworkRegistry:
    """Return the shared FrameworkRegistry singleton."""
    return FrameworkRegistry.get_instance()


def get_offline_flag(request: Request) -> bool:
    """True if the server was started with --offline."""
    return bool(getattr(request.app.state, "offline", False))


def get_dev_mode(request: Request) -> bool:
    """True if the server was started with --dev (Vite proxy mode)."""
    return bool(getattr(request.app.state, "dev_mode", False))
