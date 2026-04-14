"""LiteLLM + Instructor client setup.

Provides a configured Instructor client that works with any LLM provider
supported by LiteLLM. Model selection is determined by (in priority order):
1. Explicit model parameter
2. CONTROLBRIDGE_LLM_MODEL environment variable
3. llm.model in controlbridge.yaml
4. Default: "gpt-4o"
"""

from __future__ import annotations

import os
from functools import lru_cache

import instructor
import litellm

# Suppress LiteLLM's verbose logging by default
litellm.suppress_debug_info = True


def get_default_model() -> str:
    """Get the default model from environment or config."""
    return os.environ.get("CONTROLBRIDGE_LLM_MODEL", "gpt-4o")


def get_temperature() -> float:
    """Get the default temperature from environment or config."""
    return float(os.environ.get("CONTROLBRIDGE_LLM_TEMPERATURE", "0.1"))


@lru_cache(maxsize=1)
def get_instructor_client() -> instructor.Instructor:
    """Get a configured Instructor client.

    Uses `instructor.from_litellm` for provider-agnostic LLM access.
    The same client works with OpenAI, Anthropic, Google, Ollama, etc.
    """
    return instructor.from_litellm(litellm.completion)


@lru_cache(maxsize=1)
def get_async_instructor_client() -> instructor.AsyncInstructor:
    """Get an async Instructor client for concurrent operations."""
    return instructor.from_litellm(litellm.acompletion)
