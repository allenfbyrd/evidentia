"""Cross-framework mapping engine.

Loads crosswalk definitions and provides bidirectional mapping between
framework controls. The mapping graph is built at startup and cached
for fast lookups during gap analysis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from controlbridge_core.models.catalog import (
    CrosswalkDefinition,
    FrameworkMapping,
)

logger = logging.getLogger(__name__)

MAPPINGS_DIR = Path(__file__).parent / "data" / "mappings"


class CrosswalkEngine:
    """Bidirectional cross-framework control mapping engine.

    Loads all available crosswalk definitions and builds an in-memory
    mapping graph for fast lookups.
    """

    def __init__(self, mappings_dir: Path | None = None) -> None:
        self._dir = mappings_dir or MAPPINGS_DIR
        # Forward index: (source_fw, source_ctl, target_fw) → [FrameworkMapping]
        self._forward: dict[tuple[str, str, str], list[FrameworkMapping]] = {}
        # Reverse index built from each forward entry
        self._reverse: dict[tuple[str, str, str], list[FrameworkMapping]] = {}
        self._crosswalks: list[CrosswalkDefinition] = []

    def load_all(self) -> None:
        """Load all crosswalk JSON files from the mappings directory."""
        if not self._dir.exists():
            logger.warning("Mappings directory not found: %s", self._dir)
            return

        for json_file in sorted(self._dir.glob("*.json")):
            self.load_crosswalk(json_file)

        logger.info(
            "Loaded %d crosswalks with %d total mappings",
            len(self._crosswalks),
            sum(len(c.mappings) for c in self._crosswalks),
        )

    def load_crosswalk(self, path: Path) -> CrosswalkDefinition:
        """Load a single crosswalk definition and index it."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        crosswalk = CrosswalkDefinition(**data)
        self._crosswalks.append(crosswalk)

        for mapping in crosswalk.mappings:
            src_key = (
                crosswalk.source_framework,
                mapping.source_control_id.upper(),
                crosswalk.target_framework,
            )
            self._forward.setdefault(src_key, []).append(mapping)

            # Reverse mapping (swap source/target)
            rev_mapping = FrameworkMapping(
                source_control_id=mapping.target_control_id,
                source_control_title=mapping.target_control_title,
                target_control_id=mapping.source_control_id,
                target_control_title=mapping.source_control_title,
                relationship=mapping.relationship,
                notes=mapping.notes,
            )
            rev_key = (
                crosswalk.target_framework,
                mapping.target_control_id.upper(),
                crosswalk.source_framework,
            )
            self._reverse.setdefault(rev_key, []).append(rev_mapping)

        return crosswalk

    def get_mapped_controls(
        self,
        source_framework: str,
        source_control_id: str,
        target_framework: str,
    ) -> list[FrameworkMapping]:
        """Get controls in target_framework that map from source_control_id.

        Checks both forward and reverse indexes.
        """
        ctl = source_control_id.strip().upper()

        forward_key = (source_framework, ctl, target_framework)
        forward_results = self._forward.get(forward_key, [])

        reverse_key = (source_framework, ctl, target_framework)
        reverse_results = self._reverse.get(reverse_key, [])

        # Deduplicate by target_control_id
        seen: set[str] = set()
        results: list[FrameworkMapping] = []
        for m in forward_results + reverse_results:
            if m.target_control_id.upper() not in seen:
                seen.add(m.target_control_id.upper())
                results.append(m)

        return results

    def get_all_mapped_controls(
        self,
        framework: str,
        control_id: str,
    ) -> dict[str, list[FrameworkMapping]]:
        """Get all controls across ALL frameworks that map to/from this control.

        Returns a dict keyed by target framework ID.
        """
        ctl = control_id.strip().upper()
        results: dict[str, list[FrameworkMapping]] = {}

        for (src_fw, src_ctl, tgt_fw), mappings in self._forward.items():
            if src_fw == framework and src_ctl == ctl:
                results.setdefault(tgt_fw, []).extend(mappings)

        for (src_fw, src_ctl, tgt_fw), mappings in self._reverse.items():
            if src_fw == framework and src_ctl == ctl:
                results.setdefault(tgt_fw, []).extend(mappings)

        return results

    def get_cross_framework_value(
        self,
        framework: str,
        control_id: str,
    ) -> list[str]:
        """Get a flat list of 'framework:control_id' pairs that this control maps to.

        Used for gap prioritization — controls that satisfy more frameworks
        are higher value to implement.
        """
        all_mappings = self.get_all_mapped_controls(framework, control_id)
        result: list[str] = []
        for target_fw, mappings in all_mappings.items():
            for m in mappings:
                result.append(f"{target_fw}:{m.target_control_id}")
        return result

    @property
    def available_frameworks(self) -> set[str]:
        """All framework IDs that appear in loaded crosswalks."""
        frameworks: set[str] = set()
        for crosswalk in self._crosswalks:
            frameworks.add(crosswalk.source_framework)
            frameworks.add(crosswalk.target_framework)
        return frameworks
