"""Persistent gap report store.

v0.2.1 introduces this module so `controlbridge risk generate --gap-id GAP-…`
can resolve a single gap without re-running full gap analysis or needing
the user to pass `--gaps`. Every `gap analyze` run writes its report to a
user-dir directory; `risk generate` looks up the most recent report by
modification time and filters to the requested gap ID.

Location follows the same ``platformdirs``-backed convention as the user
catalog directory (``controlbridge_core.catalogs.user_dir``):

- Windows:  ``%APPDATA%\\ControlBridge\\gap_store\\``
- macOS:    ``~/Library/Application Support/controlbridge/gap_store/``
- Linux:    ``~/.local/share/controlbridge/gap_store/``

Override with the ``CONTROLBRIDGE_GAP_STORE_DIR`` environment variable
or a ``gap_store_dir`` argument to ``save_report`` / ``load_latest_report``.

File naming: ``<sha256-16hex>.json``, where the hash is computed from
``(inventory_source_file or organization) + '|' + sorted_frameworks_csv``.
This lets multiple concurrent projects coexist (different inventories +
frameworks produce different hashes) while still letting `risk generate`
pick the newest matching report.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from platformdirs import user_data_dir

from controlbridge_core.models.gap import GapAnalysisReport

logger = logging.getLogger(__name__)

GAP_STORE_ENV_VAR = "CONTROLBRIDGE_GAP_STORE_DIR"


def get_gap_store_dir(override: Path | None = None) -> Path:
    """Resolve the gap store directory.

    Precedence (matching catalogs/user_dir.get_user_catalog_dir):
      1. Explicit ``override`` argument (CLI flag or test fixture)
      2. ``CONTROLBRIDGE_GAP_STORE_DIR`` environment variable
      3. Platform default via ``platformdirs.user_data_dir``
    """
    if override is not None:
        return Path(override).expanduser().resolve()
    env = os.environ.get(GAP_STORE_ENV_VAR)
    if env:
        return Path(env).expanduser().resolve()
    return Path(user_data_dir("controlbridge", "ControlBridge")) / "gap_store"


def _compute_key(
    inventory_source: str | None, organization: str, frameworks: list[str]
) -> str:
    """Compute a stable 16-hex-char key for a (inventory, frameworks) pair.

    Uses ``inventory_source`` (absolute file path) when available since
    that's the most-specific identifier a user can have. Falls back to
    ``organization`` for in-memory inventories with no source file.
    """
    basis = inventory_source or organization
    seed = f"{basis}|{'|'.join(sorted(frameworks))}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def save_report(
    report: GapAnalysisReport,
    gap_store_dir: Path | None = None,
) -> Path:
    """Persist a gap report to the user-dir store.

    Returns the absolute path of the written JSON. The file is a plain
    ``model_dump_json(indent=2)`` of the report — no special framing, so
    the same file can be used directly with ``controlbridge risk generate
    --gaps <path>``.
    """
    store = get_gap_store_dir(gap_store_dir)
    store.mkdir(parents=True, exist_ok=True)

    key = _compute_key(
        report.inventory_source,
        report.organization,
        report.frameworks_analyzed,
    )
    out_path = store / f"{key}.json"
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Saved gap report: %s", out_path)
    return out_path


def load_latest_report(
    gap_store_dir: Path | None = None,
) -> GapAnalysisReport | None:
    """Return the most recent saved report by mtime, or None if empty.

    Callers should treat None as "no prior `gap analyze` run exists" and
    guide the user to run one first.
    """
    store = get_gap_store_dir(gap_store_dir)
    if not store.exists():
        return None

    reports = sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not reports:
        return None

    latest = reports[-1]
    logger.debug("Loading latest gap report: %s", latest)
    return GapAnalysisReport.model_validate_json(
        latest.read_text(encoding="utf-8")
    )


def list_reports(
    gap_store_dir: Path | None = None,
) -> list[Path]:
    """Return all stored report paths sorted newest-first."""
    store = get_gap_store_dir(gap_store_dir)
    if not store.exists():
        return []
    return sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
