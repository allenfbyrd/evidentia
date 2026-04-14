"""Framework registry — discovers and caches available catalogs and crosswalks.

Singleton that initializes at first use and provides the central access
point for all catalog and crosswalk operations.
"""

from __future__ import annotations

import logging
from pathlib import Path

from controlbridge_core.catalogs.crosswalk import CrosswalkEngine
from controlbridge_core.catalogs.loader import load_catalog
from controlbridge_core.models.catalog import CatalogControl, ControlCatalog

logger = logging.getLogger(__name__)


FRAMEWORK_METADATA: dict[str, dict[str, str]] = {
    "nist-800-53-rev5": {"name": "NIST SP 800-53 Rev 5 (Full)", "controls": "~1189"},
    "nist-800-53-mod": {"name": "NIST SP 800-53 Rev 5 Moderate Baseline", "controls": "~323"},
    "nist-800-53-high": {"name": "NIST SP 800-53 Rev 5 High Baseline", "controls": "~421"},
    "nist-csf-2.0": {"name": "NIST Cybersecurity Framework 2.0", "controls": "~106"},
    "soc2-tsc": {"name": "SOC 2 Trust Services Criteria 2017", "controls": "~60"},
    "iso27001-2022": {"name": "ISO/IEC 27001:2022 Annex A", "controls": "93"},
    "cis-controls-v8": {"name": "CIS Controls v8", "controls": "153"},
    "cmmc-2-level2": {"name": "CMMC 2.0 Level 2", "controls": "110"},
    "pci-dss-4": {"name": "PCI DSS 4.0", "controls": "~285"},
}


class FrameworkRegistry:
    """Central registry for framework catalogs and cross-framework mappings.

    Lazily loads catalogs on first access. Caches all loaded catalogs
    in memory for the lifetime of the process.
    """

    _instance: FrameworkRegistry | None = None

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or Path(__file__).parent / "data"
        self._catalogs: dict[str, ControlCatalog] = {}
        self._crosswalk_engine = CrosswalkEngine(
            mappings_dir=self._data_dir / "mappings"
        )
        self._crosswalk_loaded = False

    @classmethod
    def get_instance(cls) -> FrameworkRegistry:
        """Get or create the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the singleton (useful for tests)."""
        cls._instance = None

    @property
    def crosswalk(self) -> CrosswalkEngine:
        """Access the crosswalk engine (lazy-loaded)."""
        if not self._crosswalk_loaded:
            self._crosswalk_engine.load_all()
            self._crosswalk_loaded = True
        return self._crosswalk_engine

    def list_frameworks(self) -> list[dict[str, str]]:
        """List all available framework IDs with metadata."""
        return [{"id": fw_id, **meta} for fw_id, meta in FRAMEWORK_METADATA.items()]

    def get_catalog(self, framework_id: str) -> ControlCatalog:
        """Get a catalog by framework ID (cached)."""
        if framework_id not in self._catalogs:
            self._catalogs[framework_id] = load_catalog(framework_id)
        return self._catalogs[framework_id]

    def get_control(self, framework_id: str, control_id: str) -> CatalogControl | None:
        """Get a specific control from a framework catalog."""
        catalog = self.get_catalog(framework_id)
        return catalog.get_control(control_id)
