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


# Registered frameworks with backing catalog data bundled in this package.
# v0.1.1 ships 2 catalogs (NIST 800-53 Moderate sample + SOC 2 TSC stub);
# v0.2.0 will expand to ~50 frameworks across Tiers A/B/C/D via a
# manifest-driven registry. Do not re-add a framework ID here without
# also adding its catalog JSON under data/ and its filename in loader.py.
FRAMEWORK_METADATA: dict[str, dict[str, str]] = {
    "nist-800-53-mod": {
        "name": "NIST SP 800-53 Rev 5 Moderate Baseline (sample)",
        "controls": "16",
        "tier": "A",
    },
    "soc2-tsc": {
        "name": "SOC 2 Trust Services Criteria 2017 (stub — licensed content)",
        "controls": "61",
        "tier": "C",
    },
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
