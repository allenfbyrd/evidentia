"""Control gap analysis models.

Represents the difference between what a framework requires and what
an organization has implemented. The gap analyzer produces these models
as its primary output.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from controlbridge_core.models.common import ControlBridgeModel, new_id, utc_now


class GapSeverity(str, Enum):
    """Severity of a control gap based on framework requirement and implementation state."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ImplementationEffort(str, Enum):
    """Estimated effort to remediate a gap."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class GapStatus(str, Enum):
    """Current status of gap remediation."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    ACCEPTED = "accepted"
    NOT_APPLICABLE = "not_applicable"


class ControlGap(ControlBridgeModel):
    """A single control gap identified by the gap analyzer.

    Represents a framework requirement that the organization has not
    fully implemented.
    """

    id: str = Field(default_factory=new_id)
    # ── Framework requirement ──────────────────────────────────────────
    framework: str = Field(
        description="Framework ID, e.g. 'nist-800-53-mod', 'soc2-tsc'",
    )
    control_id: str = Field(
        description="Control ID within the framework, e.g. 'AC-2', 'CC6.1'",
    )
    control_title: str = Field(
        description="Human-readable control title from the catalog",
    )
    control_description: str = Field(
        description="Full control description from the catalog",
    )
    control_family: str | None = Field(
        default=None,
        description="Control family or category",
    )
    # ── Gap details ────────────────────────────────────────────────────
    gap_severity: GapSeverity = Field(
        description="Severity based on requirement level and implementation state",
    )
    implementation_status: str = Field(
        description=(
            "Current state: 'missing', 'partial', 'planned', 'not_applicable'"
        ),
    )
    gap_description: str = Field(
        description="Specific description of what is missing or incomplete",
    )
    status: GapStatus = Field(
        default=GapStatus.OPEN,
        description="Current remediation status",
    )
    # ── Cross-framework analysis ───────────────────────────────────────
    equivalent_controls_in_inventory: list[str] = Field(
        default_factory=list,
        description="Organization control IDs that partially satisfy this requirement",
    )
    cross_framework_value: list[str] = Field(
        default_factory=list,
        description="Other framework:control_id pairs that this gap also satisfies",
    )
    # ── Remediation ────────────────────────────────────────────────────
    remediation_guidance: str = Field(
        description="Actionable remediation guidance for this gap",
    )
    implementation_effort: ImplementationEffort = Field(
        description="Estimated engineering effort to close this gap",
    )
    priority_score: float = Field(
        default=0.0,
        description="Computed priority score (higher = more urgent)",
    )
    # ── Ticket tracking ────────────────────────────────────────────────
    jira_issue_key: str | None = Field(default=None)
    servicenow_ticket_id: str | None = Field(default=None)
    # ── Lifecycle ──────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=utc_now)
    remediated_at: datetime | None = Field(default=None)
    assigned_to: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)


class EfficiencyOpportunity(ControlBridgeModel):
    """A control that satisfies multiple framework requirements simultaneously.

    These are high-value implementation targets — implementing one control
    closes gaps across multiple frameworks.
    """

    control_id: str = Field(
        description="The NIST 800-53 control ID (canonical reference)",
    )
    control_title: str = Field(description="Human-readable control title")
    frameworks_satisfied: list[str] = Field(
        description="List of framework:control_id pairs this satisfies",
    )
    framework_count: int = Field(description="Number of distinct frameworks satisfied")
    total_gaps_closed: int = Field(
        description="Total number of gap entries that would be closed",
    )
    implementation_effort: ImplementationEffort = Field(
        description="Estimated effort to implement",
    )
    value_score: float = Field(
        description="Efficiency value score = total_gaps_closed / effort_weight",
    )


class GapAnalysisReport(ControlBridgeModel):
    """Complete gap analysis report.

    The primary output of the gap analyzer. Contains all identified gaps,
    efficiency opportunities, and a prioritized remediation roadmap.
    """

    id: str = Field(default_factory=new_id)
    organization: str = Field(
        description="Organization name from the control inventory",
    )
    frameworks_analyzed: list[str] = Field(
        description="Framework IDs that were analyzed",
    )
    analyzed_at: datetime = Field(default_factory=utc_now)
    # ── Summary statistics ─────────────────────────────────────────────
    total_controls_required: int = Field(
        description="Total unique controls required across all analyzed frameworks",
    )
    total_controls_in_inventory: int = Field(
        description="Total controls in the organization's inventory",
    )
    total_gaps: int
    critical_gaps: int
    high_gaps: int
    medium_gaps: int
    low_gaps: int
    informational_gaps: int = Field(default=0)
    coverage_percentage: float = Field(
        description="Percentage of required controls that are fully implemented",
    )
    # ── Detail ─────────────────────────────────────────────────────────
    gaps: list[ControlGap] = Field(
        description="All identified gaps, sorted by priority_score descending",
    )
    efficiency_opportunities: list[EfficiencyOpportunity] = Field(
        default_factory=list,
        description="Controls that satisfy 3+ framework requirements",
    )
    prioritized_roadmap: list[str] = Field(
        default_factory=list,
        description="Ordered list of gap IDs by descending priority_score",
    )
    # ── Metadata ───────────────────────────────────────────────────────
    inventory_source: str | None = Field(
        default=None,
        description="Path to the inventory file used",
    )
    controlbridge_version: str = Field(default="0.1.0")
    notes: str | None = Field(default=None)
