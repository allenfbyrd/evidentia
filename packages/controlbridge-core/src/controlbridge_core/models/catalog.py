"""Framework catalog models.

Represents the controls required by a compliance framework. These are
loaded from bundled OSCAL JSON catalogs and used as the "target state"
in gap analysis.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, PrivateAttr

from controlbridge_core.models.common import ControlBridgeModel


class CatalogControl(ControlBridgeModel):
    """A single control from a framework catalog."""

    id: str = Field(description="Control ID, e.g. 'AC-2', 'CC6.1'")
    title: str = Field(description="Control title")
    description: str = Field(description="Full control description")
    family: str | None = Field(default=None, description="Control family/group")
    class_: str | None = Field(
        default=None,
        alias="class",
        description="Control class: 'technical', 'operational', 'management'",
    )
    priority: str | None = Field(
        default=None,
        description="NIST priority: 'P1' (most critical) through 'P3'",
    )
    baseline_impact: list[str] = Field(
        default_factory=list,
        description="Baselines this control belongs to: ['low', 'moderate', 'high']",
    )
    enhancements: list[CatalogControl] = Field(
        default_factory=list,
        description="Control enhancements (sub-controls)",
    )
    related_controls: list[str] = Field(
        default_factory=list,
        description="IDs of related controls within the same framework",
    )
    assessment_objectives: list[str] = Field(
        default_factory=list,
        description="Assessment objectives from SP 800-53A",
    )
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Organization-defined parameters and their default values",
    )
    tier: str | None = Field(
        default=None,
        description="Redistribution tier: 'A' (public domain), 'B' (free-restricted), "
        "'C' (copyrighted, license required), 'D' (government regulation)",
    )
    license_required: bool = Field(
        default=False,
        description="True if this control's authoritative text is under copyright "
        "and this entry is a stub — users must supply their own licensed copy",
    )
    license_url: str | None = Field(
        default=None,
        description="URL to the authoritative source where licensed control text can be obtained",
    )
    placeholder: bool = Field(
        default=False,
        description="True if the description field is a placeholder rather than "
        "authoritative control text (pairs with license_required for Tier C stubs)",
    )


class ControlCatalog(ControlBridgeModel):
    """A complete framework catalog containing all controls.

    Loaded from bundled OSCAL JSON files. Provides indexed access
    to controls by ID and family.
    """

    framework_id: str = Field(
        description="Canonical framework ID, e.g. 'nist-800-53-rev5'",
    )
    framework_name: str = Field(
        description="Human-readable name, e.g. 'NIST SP 800-53 Revision 5'",
    )
    version: str = Field(
        description="Framework version, e.g. 'Rev 5', '2022', 'v8'",
    )
    source: str = Field(
        description="Source of the catalog data, e.g. 'usnistgov/oscal-content'",
    )
    controls: list[CatalogControl] = Field(
        description="All controls in this catalog",
    )
    families: list[str] = Field(
        default_factory=list,
        description="List of control families in this catalog",
    )
    tier: str | None = Field(
        default=None,
        description="Redistribution tier: 'A', 'B', 'C', 'D' (see CatalogControl.tier)",
    )
    license_required: bool = Field(
        default=False,
        description="True if this catalog is a stub whose authoritative control text "
        "is copyrighted and cannot be bundled",
    )
    license_terms: str | None = Field(
        default=None,
        description="Human-readable description of licensing terms",
    )
    license_url: str | None = Field(
        default=None,
        description="URL to the authoritative source / purchase page",
    )
    placeholder: bool = Field(
        default=False,
        description="True if the catalog as a whole is a stub (all controls have placeholder text)",
    )

    # Private index for fast lookup
    _index: dict[str, CatalogControl] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Build control index after initialization."""
        self._index = {}
        for control in self.controls:
            self._index[control.id.upper()] = control
            for enhancement in control.enhancements:
                self._index[enhancement.id.upper()] = enhancement

    def get_control(self, control_id: str) -> CatalogControl | None:
        """Look up a control by ID (case-insensitive)."""
        return self._index.get(control_id.strip().upper())

    def get_family(self, family: str) -> list[CatalogControl]:
        """Get all controls in a family."""
        return [c for c in self.controls if c.family == family]

    @property
    def control_count(self) -> int:
        """Total number of controls (including enhancements)."""
        return len(self._index)


class FrameworkMapping(ControlBridgeModel):
    """A single mapping entry between two frameworks' controls."""

    source_control_id: str
    source_control_title: str | None = None
    target_control_id: str
    target_control_title: str | None = None
    relationship: str = Field(
        description="Mapping relationship: 'equivalent', 'related', 'partial', 'superset'",
    )
    notes: str | None = Field(
        default=None,
        description="Notes about this mapping relationship",
    )


class CrosswalkDefinition(ControlBridgeModel):
    """A complete crosswalk between two frameworks.

    Loaded from bundled JSON files in catalogs/data/mappings/.
    """

    source_framework: str
    target_framework: str
    version: str
    generated_at: str
    source: str = Field(
        description="Authority source for this crosswalk",
    )
    mappings: list[FrameworkMapping]

    def get_target_controls(self, source_control_id: str) -> list[FrameworkMapping]:
        """Get all target controls mapped from a source control."""
        return [
            m
            for m in self.mappings
            if m.source_control_id.upper() == source_control_id.strip().upper()
        ]

    def get_source_controls(self, target_control_id: str) -> list[FrameworkMapping]:
        """Get all source controls mapped to a target control (reverse lookup)."""
        return [
            m
            for m in self.mappings
            if m.target_control_id.upper() == target_control_id.strip().upper()
        ]
