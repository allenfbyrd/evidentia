"""Tests for the v0.2.1 persistent gap store."""

from __future__ import annotations

from pathlib import Path

from controlbridge_core.gap_store import (
    _compute_key,
    get_gap_store_dir,
    list_reports,
    load_latest_report,
    save_report,
)
from controlbridge_core.models.gap import GapAnalysisReport


def _empty_report(
    organization: str = "Test",
    frameworks: list[str] | None = None,
    source: str | None = "test.yaml",
) -> GapAnalysisReport:
    return GapAnalysisReport(
        organization=organization,
        frameworks_analyzed=frameworks or ["nist-800-53-mod"],
        total_controls_required=10,
        total_controls_in_inventory=9,
        total_gaps=0,
        critical_gaps=0,
        high_gaps=0,
        medium_gaps=0,
        low_gaps=0,
        informational_gaps=0,
        coverage_percentage=90.0,
        gaps=[],
        efficiency_opportunities=[],
        prioritized_roadmap=[],
        inventory_source=source,
    )


# -----------------------------------------------------------------------------
# get_gap_store_dir — precedence
# -----------------------------------------------------------------------------


def test_default_store_under_platformdirs(monkeypatch) -> None:
    monkeypatch.delenv("CONTROLBRIDGE_GAP_STORE_DIR", raising=False)
    path = get_gap_store_dir()
    # Platformdirs path includes ControlBridge app identifier
    assert "controlbridge" in str(path).lower() or "ControlBridge" in str(path)


def test_env_var_overrides_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTROLBRIDGE_GAP_STORE_DIR", str(tmp_path))
    assert get_gap_store_dir() == tmp_path.resolve()


def test_explicit_override_wins_over_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTROLBRIDGE_GAP_STORE_DIR", str(tmp_path / "env"))
    explicit = tmp_path / "explicit"
    assert get_gap_store_dir(explicit) == explicit.resolve()


# -----------------------------------------------------------------------------
# _compute_key — deterministic hashing
# -----------------------------------------------------------------------------


def test_compute_key_is_deterministic() -> None:
    a = _compute_key("/path/to/inv.yaml", "Acme", ["nist-800-53-mod", "soc2-tsc"])
    b = _compute_key("/path/to/inv.yaml", "Acme", ["nist-800-53-mod", "soc2-tsc"])
    assert a == b


def test_compute_key_framework_order_insensitive() -> None:
    """Same frameworks listed in different order produce the same key."""
    a = _compute_key("/inv.yaml", "Acme", ["nist-800-53-mod", "soc2-tsc"])
    b = _compute_key("/inv.yaml", "Acme", ["soc2-tsc", "nist-800-53-mod"])
    assert a == b


def test_compute_key_different_inventory_different_key() -> None:
    a = _compute_key("/inv1.yaml", "Acme", ["nist-800-53-mod"])
    b = _compute_key("/inv2.yaml", "Acme", ["nist-800-53-mod"])
    assert a != b


def test_compute_key_falls_back_to_organization() -> None:
    """When no source_file is available, organization is the basis."""
    a = _compute_key(None, "Acme", ["nist-800-53-mod"])
    b = _compute_key(None, "Acme", ["nist-800-53-mod"])
    assert a == b
    c = _compute_key(None, "DifferentOrg", ["nist-800-53-mod"])
    assert c != a


# -----------------------------------------------------------------------------
# save_report / load_latest_report — round trip
# -----------------------------------------------------------------------------


def test_save_report_creates_file_at_hashed_path(tmp_path: Path) -> None:
    report = _empty_report()
    path = save_report(report, gap_store_dir=tmp_path)
    assert path.exists()
    assert path.parent == tmp_path.resolve()
    assert path.suffix == ".json"
    assert len(path.stem) == 16  # 16-hex-char truncated sha256


def test_save_report_roundtrip_preserves_data(tmp_path: Path) -> None:
    original = _empty_report(organization="Round Trip Org")
    save_report(original, gap_store_dir=tmp_path)
    loaded = load_latest_report(gap_store_dir=tmp_path)
    assert loaded is not None
    assert loaded.organization == "Round Trip Org"


def test_load_latest_returns_none_when_empty(tmp_path: Path) -> None:
    assert load_latest_report(gap_store_dir=tmp_path) is None


def test_load_latest_returns_newest_by_mtime(tmp_path: Path) -> None:
    """With multiple reports, load_latest_report picks the newest."""
    import time

    older = _empty_report(organization="Older")
    newer = _empty_report(
        organization="Newer",
        frameworks=["cis-controls-v8.1"],
    )
    save_report(older, gap_store_dir=tmp_path)
    time.sleep(0.02)  # ensure mtime ordering
    save_report(newer, gap_store_dir=tmp_path)

    loaded = load_latest_report(gap_store_dir=tmp_path)
    assert loaded is not None
    assert loaded.organization == "Newer"


def test_save_same_key_overwrites(tmp_path: Path) -> None:
    """Two saves with the same (inventory, frameworks) overwrite at the same path."""
    r1 = _empty_report(organization="V1")
    r2 = _empty_report(organization="V2")  # same frameworks, same source → same hash
    p1 = save_report(r1, gap_store_dir=tmp_path)
    p2 = save_report(r2, gap_store_dir=tmp_path)
    assert p1 == p2
    loaded = load_latest_report(gap_store_dir=tmp_path)
    assert loaded is not None and loaded.organization == "V2"


def test_list_reports_newest_first(tmp_path: Path) -> None:
    import time

    for fw in ["cis-controls-v8.1", "nist-800-53-mod", "soc2-tsc"]:
        r = _empty_report(frameworks=[fw])
        save_report(r, gap_store_dir=tmp_path)
        time.sleep(0.02)
    listed = list_reports(gap_store_dir=tmp_path)
    assert len(listed) == 3
    # Newest first
    assert listed[0].stat().st_mtime >= listed[-1].stat().st_mtime


def test_list_reports_empty_dir_returns_empty(tmp_path: Path) -> None:
    """Missing store dir returns empty list, no exception."""
    missing = tmp_path / "nonexistent"
    assert list_reports(gap_store_dir=missing) == []
