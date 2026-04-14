"""Smoke tests for the framework registry and crosswalk engine."""

from __future__ import annotations

import pytest
from controlbridge_core.catalogs.registry import FRAMEWORK_METADATA, FrameworkRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    FrameworkRegistry.reset_instance()
    yield
    FrameworkRegistry.reset_instance()


def test_registry_singleton():
    a = FrameworkRegistry.get_instance()
    b = FrameworkRegistry.get_instance()
    assert a is b


def test_framework_metadata_contains_supported_frameworks():
    expected = {"nist-800-53-mod", "soc2-tsc"}
    assert expected.issubset(FRAMEWORK_METADATA.keys())


def test_load_bundled_nist_catalog():
    registry = FrameworkRegistry.get_instance()
    catalog = registry.get_catalog("nist-800-53-mod")
    assert catalog.framework_id == "nist-800-53-mod"
    assert len(catalog.controls) > 0
    # Check the index works
    assert catalog.get_control("AC-2") is not None
    assert catalog.get_control("ac-2") is not None  # case-insensitive


def test_load_bundled_soc2_catalog():
    registry = FrameworkRegistry.get_instance()
    catalog = registry.get_catalog("soc2-tsc")
    assert catalog.framework_id == "soc2-tsc"
    assert catalog.get_control("CC6.1") is not None


def test_crosswalk_loads_bundled_mappings():
    registry = FrameworkRegistry.get_instance()
    crosswalk = registry.crosswalk
    assert "nist-800-53-mod" in crosswalk.available_frameworks or \
           "nist-800-53-rev5" in crosswalk.available_frameworks
    # Should have at least one mapping
    mapped = crosswalk.get_all_mapped_controls("nist-800-53-mod", "AC-2")
    if not mapped:
        # The bundled crosswalk uses nist-800-53-rev5 as the source key
        mapped = crosswalk.get_all_mapped_controls("nist-800-53-rev5", "AC-2")
    assert len(mapped) > 0
