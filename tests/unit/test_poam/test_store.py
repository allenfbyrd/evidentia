"""Unit tests for evidentia_core.poam_store (v0.9.0 P1)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from evidentia_core.models.gap import (
    ControlGap,
    GapSeverity,
    ImplementationEffort,
    Milestone,
    POAMState,
)
from evidentia_core.poam_store import (
    InvalidPoamIdError,
    delete_poam,
    get_poam_store_dir,
    list_poams,
    load_poam_by_id,
    save_poam,
)


def _make_poam(
    control_id: str = "AC-2",
    severity: GapSeverity = GapSeverity.HIGH,
    milestones: list[Milestone] | None = None,
) -> ControlGap:
    return ControlGap(
        framework="nist-800-53-rev5",
        control_id=control_id,
        control_title="Account Management",
        control_description="Manage system accounts.",
        gap_severity=severity,
        implementation_status="missing",
        gap_description="No automated account-management process.",
        remediation_guidance="Implement Okta lifecycle integration.",
        implementation_effort=ImplementationEffort.MEDIUM,
        poam_milestones=milestones or [],
    )


def _make_milestone(
    target: date = date(2026, 6, 30),
    status: POAMState = POAMState.PLANNED,
    description: str = "deliver the thing",
) -> Milestone:
    return Milestone(
        target_date=target,
        description=description,
        status=status,
    )


# ── store-dir resolution ───────────────────────────────────────────


class TestGetPoamStoreDir:
    def test_explicit_override_wins(self, tmp_path: Path) -> None:
        result = get_poam_store_dir(tmp_path)
        assert result == tmp_path.expanduser().resolve()

    def test_env_var_used_when_no_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EVIDENTIA_POAM_STORE_DIR", str(tmp_path))
        result = get_poam_store_dir()
        assert result == tmp_path.expanduser().resolve()

    def test_explicit_override_beats_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_dir = tmp_path / "env"
        override = tmp_path / "override"
        monkeypatch.setenv("EVIDENTIA_POAM_STORE_DIR", str(env_dir))
        result = get_poam_store_dir(override)
        assert result == override.expanduser().resolve()

    def test_default_uses_platformdirs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("EVIDENTIA_POAM_STORE_DIR", raising=False)
        result = get_poam_store_dir()
        assert result.name == "poam_store"
        assert "evidentia" in str(result).lower()


# ── save / load roundtrip ──────────────────────────────────────────


class TestSaveAndLoad:
    def test_save_returns_path_and_creates_file(
        self, tmp_path: Path
    ) -> None:
        p = _make_poam()
        out = save_poam(p, poam_store_dir=tmp_path)
        assert out.is_file()
        assert out.parent == tmp_path
        assert out.name == f"{p.id}.json"

    def test_save_creates_store_dir_if_missing(
        self, tmp_path: Path
    ) -> None:
        store = tmp_path / "fresh"
        save_poam(_make_poam(), poam_store_dir=store)
        assert store.is_dir()

    def test_load_by_id_returns_equivalent_record(
        self, tmp_path: Path
    ) -> None:
        original = _make_poam(
            control_id="AC-3",
            milestones=[
                _make_milestone(target=date(2026, 6, 1)),
                _make_milestone(
                    target=date(2026, 9, 1),
                    status=POAMState.IN_PROGRESS,
                    description="phase 2",
                ),
            ],
        )
        save_poam(original, poam_store_dir=tmp_path)
        loaded = load_poam_by_id(original.id, poam_store_dir=tmp_path)
        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.control_id == "AC-3"
        assert len(loaded.poam_milestones) == 2
        assert loaded.poam_milestones[0].target_date == date(2026, 6, 1)
        assert loaded.poam_milestones[1].status == POAMState.IN_PROGRESS

    def test_load_unknown_id_returns_none(self, tmp_path: Path) -> None:
        # Well-formed UUID, but not on disk
        result = load_poam_by_id(
            "00000000-0000-0000-0000-000000000000",
            poam_store_dir=tmp_path,
        )
        assert result is None

    def test_overwrite_existing_record(self, tmp_path: Path) -> None:
        p = _make_poam()
        save_poam(p, poam_store_dir=tmp_path)
        # Add a milestone and re-save
        p.poam_milestones.append(_make_milestone())
        save_poam(p, poam_store_dir=tmp_path)
        loaded = load_poam_by_id(p.id, poam_store_dir=tmp_path)
        assert loaded is not None
        assert len(loaded.poam_milestones) == 1


# ── milestone updated_at refresh on state change ───────────────────


class TestMilestoneUpdatedAtRefresh:
    def test_changed_status_refreshes_milestone_updated_at(
        self, tmp_path: Path
    ) -> None:
        m = _make_milestone()
        original_ts = m.updated_at
        p = _make_poam(milestones=[m])
        save_poam(p, poam_store_dir=tmp_path)

        # Mutate the milestone's status and re-save
        p.poam_milestones[0].status = POAMState.IN_PROGRESS
        save_poam(p, poam_store_dir=tmp_path)
        loaded = load_poam_by_id(p.id, poam_store_dir=tmp_path)
        assert loaded is not None
        assert loaded.poam_milestones[0].updated_at > original_ts

    def test_unchanged_state_preserves_updated_at(
        self, tmp_path: Path
    ) -> None:
        m = _make_milestone()
        original_ts = m.updated_at
        p = _make_poam(milestones=[m])
        save_poam(p, poam_store_dir=tmp_path)
        # Re-save without changing status
        save_poam(p, poam_store_dir=tmp_path)
        loaded = load_poam_by_id(p.id, poam_store_dir=tmp_path)
        assert loaded is not None
        # The original ts should be preserved (no change happened)
        assert loaded.poam_milestones[0].updated_at == original_ts


# ── ID validation ──────────────────────────────────────────────────


class TestInvalidIds:
    def test_load_with_path_traversal_id_raises(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(InvalidPoamIdError):
            load_poam_by_id("../etc/passwd", poam_store_dir=tmp_path)

    def test_load_with_empty_id_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidPoamIdError):
            load_poam_by_id("", poam_store_dir=tmp_path)

    def test_delete_with_invalid_id_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidPoamIdError):
            delete_poam("not-a-uuid", poam_store_dir=tmp_path)

    def test_invalid_id_subclasses_value_error(
        self, tmp_path: Path
    ) -> None:
        # Existing ``except ValueError`` handlers continue to work.
        with pytest.raises(ValueError):
            load_poam_by_id("../bad", poam_store_dir=tmp_path)


# ── list_poams ─────────────────────────────────────────────────────


class TestListPoams:
    def test_empty_store_returns_empty_list(self, tmp_path: Path) -> None:
        assert list_poams(poam_store_dir=tmp_path) == []

    def test_non_existent_store_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        result = list_poams(poam_store_dir=tmp_path / "missing")
        assert result == []

    def test_sorts_by_severity_descending(self, tmp_path: Path) -> None:
        low = _make_poam(control_id="AC-1", severity=GapSeverity.LOW)
        critical = _make_poam(
            control_id="AC-2", severity=GapSeverity.CRITICAL
        )
        medium = _make_poam(control_id="AC-3", severity=GapSeverity.MEDIUM)
        for p in [low, critical, medium]:
            save_poam(p, poam_store_dir=tmp_path)
        result = list_poams(poam_store_dir=tmp_path)
        assert [p.gap_severity for p in result] == [
            GapSeverity.CRITICAL,
            GapSeverity.MEDIUM,
            GapSeverity.LOW,
        ]

    def test_secondary_sort_open_milestones_first(
        self, tmp_path: Path
    ) -> None:
        # Both HIGH severity; one has an open milestone, the other
        # is fully closed.
        with_open = _make_poam(
            control_id="AC-2",
            severity=GapSeverity.HIGH,
            milestones=[
                _make_milestone(
                    target=date(2026, 6, 1),
                    status=POAMState.IN_PROGRESS,
                )
            ],
        )
        all_closed = _make_poam(
            control_id="AC-3",
            severity=GapSeverity.HIGH,
            milestones=[
                _make_milestone(
                    target=date(2026, 5, 1),
                    status=POAMState.COMPLETED,
                )
            ],
        )
        save_poam(all_closed, poam_store_dir=tmp_path)
        save_poam(with_open, poam_store_dir=tmp_path)
        result = list_poams(poam_store_dir=tmp_path)
        # Open work first, then fully-closed.
        assert result[0].control_id == "AC-2"
        assert result[1].control_id == "AC-3"

    def test_skips_malformed_files_with_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        save_poam(_make_poam(), poam_store_dir=tmp_path)
        # Drop a junk file with a UUID-shaped name
        junk = tmp_path / "00000000-0000-0000-0000-000000000000.json"
        junk.write_text("not valid json", encoding="utf-8")
        with caplog.at_level("WARNING"):
            result = list_poams(poam_store_dir=tmp_path)
        assert len(result) == 1
        assert any(
            "Skipping malformed POA&M record" in r.message
            for r in caplog.records
        )


# ── delete_poam ────────────────────────────────────────────────────


class TestDeletePoam:
    def test_delete_existing_returns_true(self, tmp_path: Path) -> None:
        p = _make_poam()
        save_poam(p, poam_store_dir=tmp_path)
        assert delete_poam(p.id, poam_store_dir=tmp_path)
        # Subsequent load returns None
        assert load_poam_by_id(p.id, poam_store_dir=tmp_path) is None

    def test_delete_unknown_returns_false(self, tmp_path: Path) -> None:
        result = delete_poam(
            "00000000-0000-0000-0000-000000000000",
            poam_store_dir=tmp_path,
        )
        assert result is False
