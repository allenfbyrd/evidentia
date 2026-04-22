"""Risk-generation router — SSE-streamed LLM risk statements.

``POST /api/risk/generate`` runs an asyncio fan-out over the selected
gaps, streaming per-gap progress events to the browser. The generator
reuses :class:`evidentia_ai.RiskStatementGenerator` (which already
exposes an async ``agenerate`` path via ``get_async_instructor_client``),
so offline-mode enforcement works identically to the CLI path.

Stream event shape (JSON-per-message, SSE ``event: message`` default)::

    {"phase": "start",    "total": 10}
    {"phase": "progress", "gap_id": "GAP-0001", "index": 0, "total": 10,
     "status": "generating"}
    {"phase": "progress", "gap_id": "GAP-0001", "index": 0, "total": 10,
     "status": "done", "risk": <RiskStatement>}
    {"phase": "error",    "gap_id": "GAP-0002", "detail": "..."}
    {"phase": "done",     "generated": 9, "failed": 1}
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from evidentia_core.gap_store import get_gap_store_dir
from evidentia_core.models.gap import ControlGap, GapAnalysisReport
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from evidentia_api.schemas import RiskGenerateRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_report(key: str) -> GapAnalysisReport:
    if not all(c in "0123456789abcdef" for c in key) or len(key) != 16:
        raise HTTPException(
            status_code=422,
            detail="Invalid report key format (expected 16 hex characters).",
        )
    path = get_gap_store_dir() / f"{key}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Report {key} not found.")
    return GapAnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))


def _pick_gaps(
    report: GapAnalysisReport,
    gap_ids: list[str] | None,
    top_n: int,
) -> list[ControlGap]:
    if gap_ids:
        wanted = set(gap_ids)
        return [g for g in report.gaps if g.id in wanted]
    return sorted(
        report.gaps, key=lambda g: g.priority_score, reverse=True
    )[:top_n]


async def _stream_risk_generation(
    report: GapAnalysisReport,
    selected_gaps: list[ControlGap],
    model: str | None,
    context_path: Path | None,
) -> AsyncIterator[str]:
    """Produce SSE-compatible JSON strings for each generation phase."""
    # Deferred import: RiskStatementGenerator pulls in LiteLLM which is
    # expensive to load on cold-start. The import only fires on the first
    # /api/risk/generate call.
    try:
        from evidentia_ai.risk_statements.generator import (
            RiskStatementGenerator,
        )
    except ImportError as e:  # pragma: no cover — evidentia-ai is required
        yield json.dumps({"phase": "error", "detail": f"evidentia-ai not available: {e}"})
        return

    total = len(selected_gaps)
    yield json.dumps({"phase": "start", "total": total})

    if total == 0:
        yield json.dumps({"phase": "done", "generated": 0, "failed": 0})
        return

    generator = RiskStatementGenerator(model=model) if model else RiskStatementGenerator()

    # Load context. RiskStatementGenerator requires a typed SystemContext;
    # there's no raw-dict overload. If no path given or the file can't be
    # parsed, the endpoint fails fast rather than generating risks with
    # empty org context (which produces near-useless statements).
    from evidentia_ai.risk_statements.templates import SystemContext

    if context_path is None or not context_path.is_file():
        yield json.dumps(
            {
                "phase": "error",
                "detail": (
                    "system_context YAML not found. Pass context_path pointing at "
                    "a valid system-context.yaml; see `evidentia init` for a template."
                ),
            }
        )
        return
    try:
        system_context = SystemContext.from_yaml(context_path)
    except Exception as e:
        logger.warning("Malformed system context %s: %s", context_path, e)
        yield json.dumps(
            {"phase": "error", "detail": f"Could not load system_context: {e}"}
        )
        return

    generated = 0
    failed = 0

    # Use asyncio.as_completed for true parallelism. Streaming in arrival
    # order keeps the UI responsive even if one gap is slow.
    tasks: list[
        asyncio.Task[tuple[int, ControlGap, object | None, str | None]]
    ] = []

    async def _one(
        index: int, gap: ControlGap
    ) -> tuple[int, ControlGap, object | None, str | None]:
        try:
            # `generate_async` is the async path shipped since v0.3.0.
            risk = await generator.generate_async(gap, system_context)
            return index, gap, risk, None
        except Exception as e:
            logger.exception("Risk generation failed for gap %s", gap.id)
            return index, gap, None, str(e)

    for idx, gap in enumerate(selected_gaps):
        tasks.append(asyncio.create_task(_one(idx, gap)))
        # Emit "generating" status as each task is scheduled so the UI can
        # show a progress row per gap immediately.
        yield json.dumps(
            {
                "phase": "progress",
                "gap_id": gap.id,
                "control_id": gap.control_id,
                "framework": gap.framework,
                "index": idx,
                "total": total,
                "status": "generating",
            }
        )

    for coro in asyncio.as_completed(tasks):
        index, gap, risk, err = await coro
        if risk is not None:
            generated += 1
            risk_payload = (
                risk.model_dump(mode="json")
                if hasattr(risk, "model_dump")
                else risk
            )
            yield json.dumps(
                {
                    "phase": "progress",
                    "gap_id": gap.id,
                    "control_id": gap.control_id,
                    "framework": gap.framework,
                    "index": index,
                    "total": total,
                    "status": "done",
                    "risk": risk_payload,
                }
            )
        else:
            failed += 1
            yield json.dumps(
                {
                    "phase": "error",
                    "gap_id": gap.id,
                    "control_id": gap.control_id,
                    "framework": gap.framework,
                    "index": index,
                    "total": total,
                    "detail": err,
                }
            )

    yield json.dumps({"phase": "done", "generated": generated, "failed": failed})


@router.post("/risk/generate")
async def generate(payload: RiskGenerateRequest) -> EventSourceResponse:
    """Generate risk statements for selected gaps, streaming progress via SSE."""
    report = _load_report(payload.report_key)
    selected = _pick_gaps(report, payload.gap_ids, payload.top_n)

    async def _event_stream() -> AsyncIterator[dict[str, str]]:
        async for chunk in _stream_risk_generation(
            report=report,
            selected_gaps=selected,
            model=payload.model,
            context_path=payload.context_path,
        ):
            yield {"data": chunk}

    return EventSourceResponse(_event_stream())
