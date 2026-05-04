"""Unit tests for ``scripts/bump_version.py``.

The bump script is the canonical entry point for atomic version
bumps across the monorepo. v0.7.12 P0.5 closes the inter-package
pin propagation foot-gun surfaced during the v0.7.11 fresh-venv
install (where pip resolved a cached ``evidentia-core==0.7.10``
against a freshly-published ``evidentia==0.7.11`` because the
loose ``>=0.7.0,<0.8.0`` pin permitted any patch).

This module imports the script as a module via importlib so the
helper functions (``bump_pin_range``, ``cur_parts_str``) can be
unit-tested in isolation.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BUMP_SCRIPT_PATH = REPO_ROOT / "scripts" / "bump_version.py"


def _load_bump_module() -> Any:
    """Import scripts/bump_version.py as a module for direct testing."""
    spec = importlib.util.spec_from_file_location(
        "bump_version_under_test", BUMP_SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bump() -> Any:
    return _load_bump_module()


# ── bump_pin_range ─────────────────────────────────────────────────


class TestBumpPinRange:
    def test_same_minor_patch_bump_tightens_lower_bound(
        self, bump: Any
    ) -> None:
        """v0.7.12 P0.5 closure: same-minor patch bumps tighten the
        lower bound to the target patch version, not the minor's .0.
        """
        cur_re, tgt = bump.bump_pin_range("0.7.11", "0.7.12")
        # Replacement is the canonical tight pin
        assert tgt == ">=0.7.12,<0.8.0"
        # Pattern matches both legacy loose pins AND already-tightened
        # pins from a prior post-fix patch
        regex = re.compile(cur_re)
        assert regex.fullmatch(">=0.7.0,<0.8.0")  # legacy loose
        assert regex.fullmatch(">=0.7.10,<0.8.0")  # tightened earlier
        assert regex.fullmatch(">=0.7.11,<0.8.0")  # tightened to current
        # Hot-fix versions also flow through (X.Y.Z.W form)
        assert regex.fullmatch(">=0.7.7.1,<0.8.0")

    def test_cross_minor_bump_replaces_full_range(
        self, bump: Any
    ) -> None:
        """v0.7.X -> v0.8.0 promotes the upper bound + tightens the
        lower bound to the target."""
        cur_re, tgt = bump.bump_pin_range("0.7.12", "0.8.0")
        assert tgt == ">=0.8.0,<0.9.0"
        regex = re.compile(cur_re)
        assert regex.fullmatch(">=0.7.12,<0.8.0")
        assert regex.fullmatch(">=0.7.0,<0.8.0")
        # Doesn't match the new range (avoids no-op rewrite loops)
        assert not regex.fullmatch(">=0.8.0,<0.9.0")

    def test_pin_pattern_does_not_match_unrelated_versions(
        self, bump: Any
    ) -> None:
        """The regex is anchored to the current major.minor; pins
        from other minors are NOT rewritten by accident."""
        cur_re, _ = bump.bump_pin_range("0.7.11", "0.7.12")
        regex = re.compile(cur_re)
        assert not regex.fullmatch(">=0.6.0,<0.7.0")
        assert not regex.fullmatch(">=0.8.0,<0.9.0")
        assert not regex.fullmatch(">=1.0.0,<2.0.0")

    @pytest.mark.parametrize(
        "current, target, expected_target_pin",
        [
            ("0.7.11", "0.7.12", ">=0.7.12,<0.8.0"),
            ("0.7.0", "0.7.1", ">=0.7.1,<0.8.0"),
            ("0.7.12", "0.8.0", ">=0.8.0,<0.9.0"),
            ("0.8.0", "0.9.0", ">=0.9.0,<0.10.0"),
            # Major bump (hypothetical v1.0.0)
            ("0.9.5", "1.0.0", ">=1.0.0,<1.1.0"),
        ],
    )
    def test_target_pin_uses_full_target_version_as_lower_bound(
        self,
        bump: Any,
        current: str,
        target: str,
        expected_target_pin: str,
    ) -> None:
        """The new pin's lower bound equals the FULL target version,
        not the minor's `.0`. This is the closure of the v0.7.11
        propagation foot-gun.
        """
        _, tgt = bump.bump_pin_range(current, target)
        assert tgt == expected_target_pin


class TestCurPartsStr:
    @pytest.mark.parametrize(
        "version, expected",
        [
            ("0.7.11", "0.7"),
            ("0.7.12", "0.7"),
            ("0.8.0", "0.8"),
            ("1.0.0", "1.0"),
            # Hot-fix variant (X.Y.Z.W)
            ("0.7.7.1", "0.7"),
        ],
    )
    def test_returns_major_minor_slice(
        self, bump: Any, version: str, expected: str
    ) -> None:
        assert bump.cur_parts_str(version) == expected
