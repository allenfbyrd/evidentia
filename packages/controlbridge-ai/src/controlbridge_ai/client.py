"""LiteLLM + Instructor client setup.

Provides a configured Instructor client that works with any LLM provider
supported by LiteLLM. Model selection is determined by (in priority order):
1. Explicit model parameter
2. CONTROLBRIDGE_LLM_MODEL environment variable
3. llm.model in controlbridge.yaml
4. Default: "gpt-4o"

v0.4.0: every completion call is guarded by
:func:`controlbridge_core.network_guard.check_llm_model`. When offline
mode is on (set by the CLI's ``--offline`` flag or the FastAPI app's
``app.state.offline``), cloud models raise :class:`OfflineViolationError`
before any network IO is issued. Local models (``ollama/*``, ``vllm/*``)
and custom endpoints pointing at loopback / RFC-1918 pass through.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import instructor
import litellm
from controlbridge_core.network_guard import check_llm_model

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True


def get_default_model() -> str:
    """Get the default model from environment or config."""
    return os.environ.get("CONTROLBRIDGE_LLM_MODEL", "gpt-4o")


def get_temperature() -> float:
    """Get the default temperature from environment or config."""
    return float(os.environ.get("CONTROLBRIDGE_LLM_TEMPERATURE", "0.1"))


def _guarded_completion(*args: Any, **kwargs: Any) -> Any:
    """Sync wrapper around ``litellm.completion`` that enforces offline mode."""
    model = kwargs.get("model", "")
    api_base = kwargs.get("api_base") or kwargs.get("base_url")
    check_llm_model(model, api_base=api_base, subsystem="controlbridge_ai")
    return litellm.completion(*args, **kwargs)


async def _guarded_acompletion(*args: Any, **kwargs: Any) -> Any:
    """Async wrapper around ``litellm.acompletion`` that enforces offline mode."""
    model = kwargs.get("model", "")
    api_base = kwargs.get("api_base") or kwargs.get("base_url")
    check_llm_model(model, api_base=api_base, subsystem="controlbridge_ai")
    return await litellm.acompletion(*args, **kwargs)


@lru_cache(maxsize=1)
def get_instructor_client() -> instructor.Instructor:
    """Get a configured Instructor client.

    Uses `instructor.from_litellm` with a guarded completion wrapper so
    air-gapped mode stops cloud LLM calls before they leave the process.
    """
    return instructor.from_litellm(_guarded_completion)


@lru_cache(maxsize=1)
def get_async_instructor_client() -> instructor.AsyncInstructor:
    """Get an async Instructor client for concurrent operations.

    Same guarded-completion wrapper as the sync client — concurrent
    calls (e.g. "generate risk statements for top 10 gaps in parallel")
    get the same offline enforcement.
    """
    return instructor.from_litellm(_guarded_acompletion)
