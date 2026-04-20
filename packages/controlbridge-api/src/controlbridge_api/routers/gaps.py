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

from controlbridge_core.gap_analyzer.analyzer import GapAnalyzer
from controlbridge_core.gap_analyzer.inventory import load_inventory
from controlbridge_core.gap_diff import compute_gap_diff
from controlbridge_core.gap_store import (
    get_gap_store_dir,
    list_reports,
    save_report,
)
from controlbridge_core.models.gap import GapAnalysisReport
from controlbridge_core.models.gap_diff import GapDiff
from fastapi import APIRouter, HTTPException

from controlbridge_api.schemas import GapAnalyzeRequest, GapDiffRequest

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
    fd = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="w", encoding="utf-8", suffix=suffix, delete=False
    )
    try:
        fd.write(content)
        fd.flush()
        return Path(fd.name)
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
            status_code=422,
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
            inventory_source = payload.inventory_path

        try:
            inventory = load_inventory(inventory_source)
        except (FileNotFoundError, ValueError) as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

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
    # The key is ``sha256-16hex`` — validate shape defensively to prevent
    # directory-traversal attacks via ``../`` segments.
    if not all(c in "0123456789abcdef" for c in key) or len(key) != 16:
        raise HTTPException(
            status_code=422,
            detail="Invalid report key format (expected 16 hex characters).",
        )

    path = get_gap_store_dir() / f"{key}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Report {key} not found.")

    return GapAnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))


@router.post("/gap/diff", response_model=GapDiff)
async def diff(payload: GapDiffRequest) -> GapDiff:
    """Compute a diff between two saved gap reports.

    Referenced by the /gap/diff page: user picks base + head from the
    reports list, clicks "Compare", and the result drives the summary +
    per-entry table.
    """
    store = get_gap_store_dir()

    def valid(k: str) -> bool:
        return all(c in "0123456789abcdef" for c in k) and len(k) == 16

    for label, key in (("base", payload.base_key), ("head", payload.head_key)):
        if not valid(key):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid {label} key format (expected 16 hex characters).",
            )

    base_path = store / f"{payload.base_key}.json"
    head_path = store / f"{payload.head_key}.json"
    if not base_path.is_file():
        raise HTTPException(status_code=404, detail=f"Base report {payload.base_key} not found.")
    if not head_path.is_file():
        raise HTTPException(status_code=404, detail=f"Head report {payload.head_key} not found.")

    base = GapAnalysisReport.model_validate_json(base_path.read_text(encoding="utf-8"))
    head = GapAnalysisReport.model_validate_json(head_path.read_text(encoding="utf-8"))
    return compute_gap_diff(base, head)
