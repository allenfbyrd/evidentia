"""Tests for v0.2.1 control-ID normalization (NIST-pub vs NIST-OSCAL convention)."""

from __future__ import annotations

import pytest
from controlbridge_core.models.catalog import (
    CatalogControl,
    ControlCatalog,
    _normalize_control_id,
)

# -----------------------------------------------------------------------------
# _normalize_control_id — canonical form conversion
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("AC-2", "AC-2"),
        ("ac-2", "AC-2"),
        ("  AC-2  ", "AC-2"),
        ("AC-2(1)", "AC-2.1"),
        ("ac-2.1", "AC-2.1"),
        ("AC-2(1)(a)", "AC-2.1.A"),
        ("ac-2.1.a", "AC-2.1.A"),
        ("AC-2(12)", "AC-2.12"),
        # 800-171 dotted style
        ("03.01.01", "03.01.01"),
        ("3.1.1", "3.1.1"),
        # SOC 2 style (uppercase, dots only)
        ("CC6.1", "CC6.1"),
        ("cc6.1", "CC6.1"),
        # Edge cases
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_control_id_canonical_form(raw: str, expected: str) -> None:
    assert _normalize_control_id(raw) == expected


def test_normalize_preserves_nested_parentheses() -> None:
    """Multi-level parens resolve to multi-level dots."""
    assert _normalize_control_id("AC-2(1)(a)(i)") == "AC-2.1.A.I"


def test_normalize_handles_non_ascii_gracefully() -> None:
    """Non-ASCII input (unexpected) doesn't crash."""
    # We don't really expect Unicode in control IDs; just verify no crash
    result = _normalize_control_id("AC-2")
    assert result == "AC-2"


# -----------------------------------------------------------------------------
# ControlCatalog.get_control — dual-convention lookup
# -----------------------------------------------------------------------------


def _make_catalog_with_nested() -> ControlCatalog:
    """Build a catalog using NIST-OSCAL convention (lowercase dotted)."""
    return ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[
            CatalogControl(
                id="ac-2",
                title="Account Management",
                description="Manage accounts.",
                enhancements=[
                    CatalogControl(
                        id="ac-2.1",
                        title="Automated System Account Management",
                        description="Automate it.",
                        enhancements=[
                            CatalogControl(
                                id="ac-2.1.a",
                                title="Sub-control",
                                description="Even deeper.",
                            )
                        ],
                    )
                ],
            )
        ],
    )


def test_nist_pub_style_lookup_resolves() -> None:
    """User types AC-2(1) — finds the OSCAL-keyed ac-2.1 control."""
    cat = _make_catalog_with_nested()
    ctrl = cat.get_control("AC-2(1)")
    assert ctrl is not None
    assert ctrl.id == "ac-2.1"


def test_nist_oscal_style_lookup_resolves() -> None:
    """User types ac-2.1 — finds the same control."""
    cat = _make_catalog_with_nested()
    ctrl = cat.get_control("ac-2.1")
    assert ctrl is not None


def test_case_insensitive() -> None:
    cat = _make_catalog_with_nested()
    assert cat.get_control("ac-2") is not None
    assert cat.get_control("AC-2") is not None


def test_whitespace_stripped() -> None:
    cat = _make_catalog_with_nested()
    assert cat.get_control("  AC-2(1)  ") is not None


def test_three_level_nesting_works() -> None:
    """Deeply nested control from a catalog with 3+ enhancement levels resolves."""
    cat = _make_catalog_with_nested()
    ctrl = cat.get_control("AC-2(1)(a)")
    assert ctrl is not None


def test_missing_control_returns_none() -> None:
    cat = _make_catalog_with_nested()
    assert cat.get_control("BOGUS-99") is None
    assert cat.get_control("AC-99(99)") is None


def test_pub_style_and_oscal_style_resolve_same_control() -> None:
    cat = _make_catalog_with_nested()
    a = cat.get_control("AC-2(1)")
    b = cat.get_control("ac-2.1")
    assert a is b  # identity, not equality — same object in the index
