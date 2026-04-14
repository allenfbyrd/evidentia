"""Control implementation and inventory models.

Represents an organization's current state of control implementation.
This is the input to gap analysis — "what do we have today?"
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from controlbridge_core.models.common import ControlBridgeModel, utc_now


class ControlStatus(str, Enum):
    """Implementation status of a control within an organization."""

    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    PLANNED = "planned"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_APPLICABLE = "not_applicable"


class ControlImplementation(ControlBridgeModel):
    """Represents a single control as implemented by the organization.

    This is not a catalog control (what the framework requires) but an
    organizational control (what the org actually does). The gap analyzer
    compares these against catalog controls to find gaps.
    """

    id: str = Field(
        description=(
            "Organization-defined control ID, typically matching framework IDs. "
            "E.g. 'AC-2', 'CC6.1', 'A.9.2.1'"
        )
    )
    title: str | None = Field(
        default=None,
        description="Human-readable control title",
    )
    description: str | None = Field(
        default=None,
        description="Description of how the organization implements this control",
    )
    status: ControlStatus = Field(
        description="Current implementation status",
    )
    implementation_notes: str | None = Field(
        default=None,
        description=(
            "Free-text notes on implementation details, compensating controls, "
            "or planned improvements"
        ),
    )
    responsible_roles: list[str] = Field(
        default_factory=list,
        description="Roles or teams responsible for this control",
    )
    evidence_references: list[str] = Field(
        default_factory=list,
        description="Paths, URIs, or IDs pointing to supporting evidence artifacts",
    )
    last_assessed: datetime | None = Field(
        default=None,
        description="When this control was last assessed or validated",
    )
    owner: str | None = Field(
        default=None,
        description="Email or name of the control owner",
    )
    frameworks: list[str] = Field(
        default_factory=list,
        description="Frameworks this control is claimed to satisfy",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Arbitrary tags for filtering and organization",
    )


class ControlInventory(ControlBridgeModel):
    """An organization's complete control inventory.

    This is the primary input to gap analysis. It can be loaded from:
    - ControlBridge YAML format (preferred)
    - CSV with header mapping
    - OSCAL component definition JSON
    - CISO Assistant JSON export
    """

    organization: str = Field(
        description="Organization name, used in report headers",
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="When this inventory was created",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="When this inventory was last updated",
    )
    controls: list[ControlImplementation] = Field(
        description="List of all control implementations",
    )
    source_format: str = Field(
        default="controlbridge",
        description="Format of source data: 'controlbridge', 'oscal', 'csv', 'ciso-assistant'",
    )
    source_file: str | None = Field(
        default=None,
        description="Path to the source file this inventory was loaded from",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata from the source format",
    )

    @property
    def implemented_count(self) -> int:
        """Count of fully implemented controls."""
        return sum(
            1 for c in self.controls if c.status == ControlStatus.IMPLEMENTED.value
        )

    @property
    def total_count(self) -> int:
        """Total number of controls in inventory."""
        return len(self.controls)

    def get_control(self, control_id: str) -> ControlImplementation | None:
        """Look up a control by ID (case-insensitive, whitespace-normalized)."""
        normalized = control_id.strip().upper().replace(" ", "-")
        for control in self.controls:
            if control.id.strip().upper().replace(" ", "-") == normalized:
                return control
        return None
