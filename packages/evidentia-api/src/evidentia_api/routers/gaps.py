"""Gap-analysis router — run + list + diff gap reports.

Endpoints:
- ``POST /api/gap/analyze`` — run a GapAnalyzer pass and persist to gap_store
- ``GET /api/gap/reports`` — list saved reports (newest first)
- ``GET /api/gap/reports/{key}`` — load a specific saved report
- ``POST /api/gap/diff`` — compute a diff between two saved reports

Inventory input accepts either a server-side file path (typical for CLI
integration) or an inline YAML/JSON blob (typical for browser upload).
"""

from __future__ import annotations

import logging
import tempfile
from datetime import UTC
from pathlib import Path

from evidentia_core.gap_analyzer.analyzer import GapAnalyzer
from evidentia_core.gap_analyzer.inventory import load_inventory
from evidentia_core.gap_diff import compute_gap_diff
from evidentia_core.gap_store import (
    InvalidReportKeyError,
    get_gap_store_dir,
    list_reports,
    load_report_by_key,
    save_report,
)
from evidentia_core.models.gap import GapAnalysisReport
from evidentia_core.models.gap_diff import GapDiff
from evidentia_core.security.paths import (
    PathTraversalError,
    validate_within,
)
from fastapi import APIRouter, HTTPException

from evidentia_api.schemas import GapAnalyzeRequest, GapDiffRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _materialize_inventory_content(
    content: str, inventory_format: str
) -> Path:
    """Write inline inventory content to a temp file so ``load_inventory`` can parse it.

    The existing loader is path-based (auto-detects format by extension);
    the API accepts inline strings for browser-originated uploads. Rather
    than duplicate the three parser entry points, we round-trip through a
    temp file.
    """
    suffix_map = {"yaml": ".yaml", "yml": ".yaml", "csv": ".csv", "json": ".json"}
    suffix = suffix_map.get(inventory_format.lower(), ".yaml")
    # A short-lived temp file handed to the caller; the caller unlinks it
    # after load_inventory() completes. A context manager would delete the
    # file on __exit__, which is the opposite of what we want.
    tmp_root = Path(tempfile.gettempdir())
    fd = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="w", encoding="utf-8", suffix=suffix, delete=False, dir=tmp_root
    )
    try:
        fd.write(content)
        fd.flush()
        # tempfile.NamedTemporaryFile already returns a path inside the
        # tmp dir; validate_within is the CodeQL-recognizable barrier
        # that lets static analysis stop flagging downstream IO on this
        # path as a path-injection sink.
        return validate_within(Path(fd.name), tmp_root)
    finally:
        fd.close()


@router.post("/gap/analyze", response_model=GapAnalysisReport)
async def analyze(payload: GapAnalyzeRequest) -> GapAnalysisReport:
    """Run gap analysis and persist the result to the gap store.

    Returns the freshly-computed report. The persisted JSON lives under
    the user-dir gap_store and is referenced by the ``GET /api/gap/reports``
    endpoint after this call completes.
    """
    if not payload.inventory_path and not payload.inventory_content:
        raise HTTPException(
            status_code=400,
            detail="Either inventory_path or inventory_content must be provided.",
        )

    tmp_path: Path | None = None
    try:
        if payload.inventory_content:
            tmp_path = _materialize_inventory_content(
                payload.inventory_content, payload.inventory_format
            )
            inventory_source = tmp_path
        else:
            assert payload.inventory_path is not None
            # The inventory_path field is for CLI-adjacent use (a server
            # invoked locally that loads from disk). For an API exposed
            # to untrusted callers, restrict to paths inside the server's
            # current working directory — operators who need to read
            # inventories from elsewhere should pass inventory_content
            # instead of inventory_path.
            try:
                inventory_source = validate_within(
                    Path(payload.inventory_path), Path.cwd()
                )
            except PathTraversalError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            inventory = load_inventory(inventory_source)
        except (FileNotFoundError, ValueError) as e:
            # Use 400 (not 422) for runtime body-content validation errors
            # so the response shape (`{detail: string}`) matches the
            # OpenAPI declaration. 422 is reserved for Pydantic
            # auto-validation responses, which use `{detail: array}`.
            # Closes F-V08-DAST-3 schema-fidelity finding cluster.
            raise HTTPException(status_code=400, detail=str(e)) from e

        # CLI-style overrides
        if payload.organization:
            inventory.organization = payload.organization
        if payload.system_name:
            inventory.system_name = payload.system_name

        report = GapAnalyzer().analyze(inventory, payload.frameworks)
        save_report(report)
        return report
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@router.get("/gap/reports")
async def get_reports() -> dict[str, object]:
    """List saved gap reports, newest first.

    Each entry includes the storage key, mtime, byte size, and a short
    summary (organization + framework list) so the UI can render a
    listing without loading every report body.
    """
    import json
    from datetime import datetime

    entries: list[dict[str, object]] = []
    for path in list_reports():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries.append(
                {
                    "key": path.stem,
                    "mtime_iso": datetime.fromtimestamp(
                        path.stat().st_mtime, tz=UTC
                    ).isoformat(),
                    "size_bytes": path.stat().st_size,
                    "organization": data.get("organization", "(unknown)"),
                    "frameworks_analyzed": data.get("frameworks_analyzed", []),
                    "total_gaps": data.get("total_gaps", 0),
                    "critical_gaps": data.get("critical_gaps", 0),
                    "coverage_percentage": data.get("coverage_percentage"),
                }
            )
        except Exception as e:
            logger.warning("Skipping malformed report %s: %s", path, e)

    return {"total": len(entries), "reports": entries, "store_dir": str(get_gap_store_dir())}


@router.get("/gap/reports/{key}", response_model=GapAnalysisReport)
async def get_report(key: str) -> GapAnalysisReport:
    """Load a saved gap report by its storage key."""
    try:
        report = load_report_by_key(key)
    except (InvalidReportKeyError, PathTraversalError) as exc:
        # Both InvalidReportKeyError + PathTraversalError reflect
        # client-supplied bad keys; both normalize to 400 with a
        # `{detail: string}` shape (matches OpenAPI declaration —
        # closes F-V08-DAST-3 schema-fidelity finding cluster).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {key} not found.")
    return report


@router.post("/gap/diff", response_model=GapDiff)
async def diff(payload: GapDiffRequest) -> GapDiff:
    """Compute a diff between two saved gap reports.

    Referenced by the /gap/diff page: user picks base + head from the
    reports list, clicks "Compare", and the result drives the summary +
    per-entry table.
    """
    loaded: dict[str, GapAnalysisReport] = {}
    for label, key in (("base", payload.base_key), ("head", payload.head_key)):
        try:
            report = load_report_by_key(key)
        except InvalidReportKeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {label} key: {exc}",
            ) from exc
        except PathTraversalError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {label} key: {exc}",
            ) from exc
        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"{label.capitalize()} report {key} not found.",
            )
        loaded[label] = report

    return compute_gap_diff(loaded["base"], loaded["head"])
