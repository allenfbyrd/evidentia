"""Unit tests for ``scripts/check_version_consistency.py`` (v0.10.7 E4).

The consistency-check is the "never-skip-a-version-reference" gate. It reads
``scripts/version_tracked_files.yaml`` and enforces:

  1. COVERAGE  — every tracked file holds the current version where expected.
  2. NEVER-SKIP — every git-tracked file carrying a project-version literal is
     classified (tracked OR frozen); an unclassified literal is a hard fail.

These tests build tiny temp "repos" (a dir + a fake ``git ls-files`` result
via monkeypatched ``tracked_files``) so no real git / network is touched. The
script's ``check_coverage`` / ``check_never_skip`` read files relative to the
process CWD, so tests chdir into the temp dir.
"""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = REPO_ROOT / "scripts" / "check_version_consistency.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def check() -> Any:
    return _load_module("check_version_consistency_under_test", CHECK_PATH)


@pytest.fixture
def bump(check: Any) -> Any:
    """The bump_version module the check imports (for its helpers)."""
    return check._load_bump_module()


@pytest.fixture
def chdir_tmp(tmp_path: Path) -> Iterator[Path]:
    """Run the test body with CWD set to a temp dir (restored afterwards)."""
    prev = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(prev)


def _make_bump_with_tracked(
    bump: Any, monkeypatch: pytest.MonkeyPatch, tracked: list[str], packages: list[str]
) -> Any:
    """Monkeypatch the imported bump module so tracked_files() + workspace_packages()
    return controlled values, while keeping the real expand_manifest_path +
    replacements_for_kind."""
    monkeypatch.setattr(bump, "tracked_files", lambda: [Path(p) for p in tracked])
    monkeypatch.setattr(bump, "workspace_packages", lambda *a, **k: list(packages))
    return bump


# ── COVERAGE ───────────────────────────────────────────────────────────


def test_coverage_pass_when_tracked_file_current(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (chdir_tmp / "pyproject.toml").write_text(
        'version = "0.10.7"\n', encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["pyproject.toml"], [])
    manifest = {
        "tracked": [{"path": "pyproject.toml", "kind": "python_version"}],
        "frozen": [],
    }
    assert check.check_coverage(bump, manifest, "0.10.7") == []


def test_coverage_fail_when_tracked_file_stale(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # File holds the OLD version; current is 0.10.7 -> stale -> FAIL.
    (chdir_tmp / "pyproject.toml").write_text(
        'version = "0.10.6"\n', encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["pyproject.toml"], [])
    manifest = {
        "tracked": [{"path": "pyproject.toml", "kind": "python_version"}],
        "frozen": [],
    }
    failures = check.check_coverage(bump, manifest, "0.10.7")
    assert len(failures) == 1
    assert "stale tracked file pyproject.toml" in failures[0]
    assert "0.10.7" in failures[0]


def test_coverage_readme_container_tag_stale_fails(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale README container tag (the motivating bug) is caught."""
    (chdir_tmp / "README.md").write_text(
        "Container: `docker pull ghcr.io/polycentric-labs/evidentia:v0.10.6`\n",
        encoding="utf-8",
    )
    _make_bump_with_tracked(bump, monkeypatch, ["README.md"], [])
    manifest = {
        "tracked": [{"path": "README.md", "kind": "readme_container_tag"}],
        "frozen": [],
    }
    failures = check.check_coverage(bump, manifest, "0.10.7")
    assert len(failures) == 1
    assert "README.md" in failures[0]


def test_coverage_advisory_kinds_not_required(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pip_extra_pin / workspace_pins / cff_date are advisory — a file lacking
    the current version for one of those kinds does NOT fail coverage."""
    # requirements.in legitimately lags (last *published* release).
    (chdir_tmp / "requirements.in").write_text(
        "evidentia[gui]==0.9.1\n", encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["requirements.in"], [])
    manifest = {
        "tracked": [{"path": "requirements.in", "kind": "pip_extra_pin"}],
        "frozen": [],
    }
    assert check.check_coverage(bump, manifest, "0.10.7") == []


def test_coverage_missing_glob_target_fails(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tracked path/glob that matches no tracked file is a config error."""
    _make_bump_with_tracked(bump, monkeypatch, ["other.toml"], [])
    manifest = {
        "tracked": [{"path": "packages/*/pyproject.toml", "kind": "python_version"}],
        "frozen": [],
    }
    failures = check.check_coverage(bump, manifest, "0.10.7")
    assert len(failures) == 1
    assert "matched no git-tracked file" in failures[0]


# ── NEVER-SKIP ─────────────────────────────────────────────────────────


def test_never_skip_pass_when_literal_in_frozen(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A frozen file holding an OLD project version passes (historical)."""
    (chdir_tmp / "CHANGELOG.md").write_text(
        "## [0.7.0] - 2026-01-01\nInitial.\n", encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["CHANGELOG.md"], [])
    manifest = {
        "tracked": [],
        "frozen": [{"path": "CHANGELOG.md"}],
    }
    assert check.check_never_skip(bump, manifest) == []


def test_never_skip_fail_when_literal_unclassified(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unclassified file carrying a project-version literal hard-fails with
    the exact message the task specifies."""
    (chdir_tmp / "mystery.cfg").write_text(
        "some_setting = v0.10.7\n", encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["mystery.cfg"], [])
    manifest = {"tracked": [], "frozen": []}
    failures = check.check_never_skip(bump, manifest)
    assert len(failures) == 1
    assert failures[0] == (
        "untracked version reference in mystery.cfg — classify it in "
        "scripts/version_tracked_files.yaml (tracked or frozen)"
    )


def test_never_skip_classified_tracked_file_ok(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tracked file with the current literal is classified -> not flagged."""
    (chdir_tmp / "pyproject.toml").write_text(
        'version = "0.10.7"\n', encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["pyproject.toml"], [])
    manifest = {
        "tracked": [{"path": "pyproject.toml", "kind": "python_version"}],
        "frozen": [],
    }
    assert check.check_never_skip(bump, manifest) == []


def test_never_skip_glob_classification(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``docs/**`` frozen glob classifies a nested doc carrying a literal."""
    (chdir_tmp / "docs").mkdir()
    (chdir_tmp / "docs" / "sub").mkdir()
    (chdir_tmp / "docs" / "sub" / "old-plan.md").write_text(
        "Shipped in v0.8.0.\n", encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["docs/sub/old-plan.md"], [])
    manifest = {"tracked": [], "frozen": [{"path": "docs/**"}]}
    assert check.check_never_skip(bump, manifest) == []


def test_never_skip_ignores_sub_project_versions(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Small third-party dep versions (0.1.x .. 0.6.x) are below the project
    family floor (>= 0.7) and do NOT trip the gate, so a file that ONLY
    carries such a version need not be classified."""
    (chdir_tmp / "unrelated.txt").write_text(
        "annotated-types 0.6.0 and defusedxml 0.5.1\n", encoding="utf-8"
    )
    _make_bump_with_tracked(bump, monkeypatch, ["unrelated.txt"], [])
    manifest = {"tracked": [], "frozen": []}
    assert check.check_never_skip(bump, manifest) == []


def test_never_skip_binary_file_skipped(
    check: Any, bump: Any, chdir_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-UTF-8 / binary tracked file cannot carry a text literal and is
    skipped rather than crashing."""
    (chdir_tmp / "blob.bin").write_bytes(b"\xff\xfe\x00\x01binary\x00")
    _make_bump_with_tracked(bump, monkeypatch, ["blob.bin"], [])
    manifest = {"tracked": [], "frozen": []}
    assert check.check_never_skip(bump, manifest) == []


# ── End-to-end against the REAL repo manifest ──────────────────────────


def test_real_repo_passes_clean(check: Any) -> None:
    """The committed manifest + working tree must pass both invariants.

    This is the live proof that ``frozen`` is seeded comprehensively enough
    that HEAD is green (the v0.10.7 E4 acceptance gate)."""
    bump = check._load_bump_module()
    manifest = bump.load_manifest()
    current = bump.detect_current_version()
    coverage = check.check_coverage(bump, manifest, current)
    never_skip = check.check_never_skip(bump, manifest)
    assert coverage == [], f"coverage failures: {coverage}"
    assert never_skip == [], f"never-skip failures: {never_skip}"


def test_project_version_regex_matches_expected_forms(check: Any) -> None:
    rx = check.PROJECT_VERSION_RE
    assert rx.search("v0.10.7")
    assert rx.search("0.10.7")
    assert rx.search("0.7.0")
    assert rx.search("0.7.7.1")  # hot-fix form
    assert rx.search("evidentia:v0.10.8 ")
    # Below the family floor (< 0.7) — not a project version.
    assert not rx.search("annotated-types 0.6.0")
    assert not rx.search("0.1.2")
    # Not a 0.x version at all.
    assert not rx.search("python 3.12.4")
    assert not rx.search("800.53.7")
