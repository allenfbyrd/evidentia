"""Backward-compat shim.

v0.4.0 moved the config loader to :mod:`evidentia_core.config` so the
FastAPI backend (``evidentia-api``) can consume it without inducing a
circular package dependency. This module transparently re-exports the
public API so existing external consumers — and anyone who imported from
``evidentia.config`` in v0.2.x / v0.3.x — keep working unchanged.

Internal callers (CLI modules) have been updated to import directly from
``evidentia_core.config``. External users should migrate at their
convenience; a deprecation may follow in v0.5.0 but is not yet scheduled.
"""

from __future__ import annotations

from evidentia_core.config import (  # noqa: F401  re-exports
    CONFIG_FILENAME,
    EvidentiaConfig,
    LLMConfig,
    _expand_env_vars,
    _load_config_cached,
    find_config_file,
    get_default,
    load_config,
)

__all__ = [
    "CONFIG_FILENAME",
    "EvidentiaConfig",
    "LLMConfig",
    "find_config_file",
    "get_default",
    "load_config",
]
