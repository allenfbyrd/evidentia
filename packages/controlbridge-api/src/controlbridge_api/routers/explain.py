"""Explain router — plain-English control explanations.

Wraps :class:`controlbridge_ai.ExplanationGenerator` (which caches to
disk per (framework, control, model, temperature) tuple). Returns the
explanation as JSON for cached hits, or as an SSE stream for cache
misses where the LLM might take several seconds.

In v0.4.0 both paths return the same JSON shape; the SSE variant just
emits a single ``data:`` event with the result. v0.4.1 will add true
token-level streaming once LiteLLM's Anthropic streaming adapter is
confirmed stable across all configured providers.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/explain/{framework}/{control_id:path}")
async def explain(
    framework: str,
    control_id: str,
    refresh: bool = Query(
        False, description="Bypass the on-disk cache and re-generate."
    ),
    model: str | None = Query(
        None,
        description="LLM model override; falls back to CONTROLBRIDGE_LLM_MODEL/config.",
    ),
) -> EventSourceResponse:
    """Return a plain-English explanation of a control, streamed via SSE."""
    # Defer heavy imports so /api/explain is fast to register even when
    # controlbridge-ai is slow to import.
    try:
        from controlbridge_ai.explain import ExplanationGenerator
    except ImportError as e:  # pragma: no cover — controlbridge-ai is required
        raise HTTPException(
            status_code=500,
            detail=f"controlbridge-ai unavailable: {e}",
        ) from e

    from controlbridge_core.catalogs.registry import FrameworkRegistry

    registry = FrameworkRegistry.get_instance()
    try:
        catalog = registry.get_catalog(framework)
    except (FileNotFoundError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=404, detail=f"Framework '{framework}' not found."
        ) from e

    control = catalog.get_control(control_id)
    if control is None:
        raise HTTPException(
            status_code=404,
            detail=f"Control '{control_id}' not found in '{framework}'.",
        )

    gen = ExplanationGenerator(model=model) if model else ExplanationGenerator()

    async def _stream() -> AsyncIterator[dict[str, str]]:
        yield {
            "data": json.dumps(
                {"phase": "start", "framework": framework, "control_id": control.id}
            )
        }
        try:
            # Most explanation generators are synchronous; run in a thread
            # so we don't block the event loop.
            import asyncio

            if hasattr(gen, "aexplain"):
                result = await gen.aexplain(
                    control=control, framework=framework, refresh=refresh
                )
            else:
                result = await asyncio.to_thread(
                    gen.explain,
                    control=control,
                    framework=framework,
                    refresh=refresh,
                )
            payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
            yield {"data": json.dumps({"phase": "done", "explanation": payload})}
        except Exception as e:
            logger.exception("Explanation failed")
            yield {
                "data": json.dumps(
                    {"phase": "error", "detail": str(e), "type": type(e).__name__}
                )
            }

    return EventSourceResponse(_stream())
