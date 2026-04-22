"""Tests for the recursive enhancement flattener in ControlCatalog.

v0.2.0 replaced the single-level flattener with a recursive walk so
NIST 800-53 Rev 5 IDs like ``AC-2(1)(a)`` resolve via ``get_control``.
"""

from __future__ import annotations

from evidentia_core.models.catalog import CatalogControl, ControlCatalog


def _make_control(id_: str, enhancements: list[CatalogControl] | None = None) -> CatalogControl:
    return CatalogControl(
        id=id_,
        title=f"Title for {id_}",
        description=f"Description for {id_}",
        enhancements=enhancements or [],
    )


def test_flat_lookup_works() -> None:
    """Top-level controls are indexed."""
    catalog = ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[_make_control("AC-1"), _make_control("AC-2")],
    )
    assert catalog.get_control("AC-1") is not None
    assert catalog.get_control("AC-2") is not None
    assert catalog.control_count == 2


def test_one_level_enhancement_lookup() -> None:
    """First-level enhancements (AC-2(1)) are indexed."""
    enh1 = _make_control("AC-2(1)")
    enh2 = _make_control("AC-2(2)")
    catalog = ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[_make_control("AC-2", enhancements=[enh1, enh2])],
    )
    assert catalog.get_control("AC-2") is not None
    assert catalog.get_control("AC-2(1)") is not None
    assert catalog.get_control("AC-2(2)") is not None
    assert catalog.control_count == 3


def test_two_level_enhancement_lookup() -> None:
    """Two-level enhancement IDs like AC-2(1)(a) resolve (v0.2.0 fix)."""
    leaf = _make_control("AC-2(1)(a)")
    mid = _make_control("AC-2(1)", enhancements=[leaf])
    catalog = ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[_make_control("AC-2", enhancements=[mid])],
    )
    # v0.1.x lost this lookup — enhancement-of-enhancement was not indexed
    assert catalog.get_control("AC-2(1)(a)") is not None
    assert catalog.get_control("AC-2(1)") is not None
    assert catalog.get_control("AC-2") is not None
    assert catalog.control_count == 3


def test_case_insensitive_lookup() -> None:
    catalog = ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[_make_control("AC-2")],
    )
    assert catalog.get_control("ac-2") is not None
    assert catalog.get_control("Ac-2") is not None


def test_whitespace_stripped_on_lookup() -> None:
    catalog = ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[_make_control("AC-2")],
    )
    assert catalog.get_control("  AC-2  ") is not None


def test_missing_control_returns_none() -> None:
    catalog = ControlCatalog(
        framework_id="test",
        framework_name="Test",
        version="1.0",
        source="test",
        controls=[_make_control("AC-2")],
    )
    assert catalog.get_control("BOGUS-99") is None
