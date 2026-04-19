"""Config router — read / write ``controlbridge.yaml``.

GET returns the current config (walking CWD -> parents for the file).
PUT accepts a :class:`ControlBridgeConfig` payload, validates it via
Pydantic, and writes the YAML back to the same path.

No secrets ever flow through this endpoint's request/response bodies —
the ``llm`` subsection is model + temperature only (no API keys). Keys
are handled separately via the ``/api/llm-status`` endpoint, which never
returns key values, only booleans + source identifiers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from controlbridge_core.config import (
    CONFIG_FILENAME,
    ControlBridgeConfig,
    find_config_file,
    load_config,
)
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/config", response_model=ControlBridgeConfig)
async def get_config() -> ControlBridgeConfig:
    """Return the currently-loaded controlbridge.yaml contents.

    If no file exists in CWD or any parent, returns a default
    (empty) :class:`ControlBridgeConfig`.
    """
    return load_config()


@router.put("/config", response_model=ControlBridgeConfig)
async def put_config(payload: ControlBridgeConfig) -> ControlBridgeConfig:
    """Persist ``controlbridge.yaml`` with the validated payload.

    Writes to the discovered path (walking CWD -> parents), or to
    ``./controlbridge.yaml`` if none exists yet. Returns the persisted
    config (with ``source_path`` populated so callers can confirm where
    the write landed).
    """
    target = find_config_file() or (Path.cwd() / CONFIG_FILENAME)
    try:
        dumped: dict[str, Any] = payload.model_dump(
            exclude={"source_path"}, exclude_defaults=False
        )
        yaml_text = yaml.safe_dump(
            dumped, sort_keys=False, default_flow_style=False
        )
        target.write_text(yaml_text, encoding="utf-8")
    except OSError as e:
        logger.error("Failed to write %s: %s", target, e)
        raise HTTPException(
            status_code=500,
            detail=f"Could not write config to {target}: {e}",
        ) from e

    # Clear the LRU cache so subsequent reads see the new contents.
    from controlbridge_core.config import _load_config_cached

    _load_config_cached.cache_clear()

    refreshed = load_config(target)
    logger.info("Wrote %s (%d bytes)", target, len(yaml_text))
    return refreshed
