"""Security finding model for collector outputs.

Collectors produce findings (raw security observations from systems).
Findings are then mapped to evidence artifacts with control mappings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from evidentia_core.models.common import (
    EvidentiaModel,
    Severity,
    new_id,
    utc_now,
)


class FindingStatus(str, Enum):
    """Status of a security finding."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class SecurityFinding(EvidentiaModel):
    """A security finding from an evidence collector.

    Findings are the raw output of collectors — they represent a single
    observation about a system's security posture. Findings are then
    transformed into EvidenceArtifacts with control mappings.
    """

    id: str = Field(default_factory=new_id)
    title: str
    description: str
    severity: Severity
    status: FindingStatus = Field(default=FindingStatus.ACTIVE)
    # Source
    source_system: str = Field(description="E.g. 'aws-security-hub', 'github'")
    source_finding_id: str | None = Field(
        default=None,
        description="Original finding ID in the source system",
    )
    # Resource
    resource_type: str | None = Field(
        default=None,
        description="E.g. 'AWS::S3::Bucket', 'GitHub::Repository'",
    )
    resource_id: str | None = Field(
        default=None,
        description="Resource identifier in the source system",
    )
    resource_region: str | None = Field(default=None)
    resource_account: str | None = Field(default=None)
    # Control mappings
    control_ids: list[str] = Field(
        default_factory=list,
        description="NIST 800-53 control IDs this finding relates to",
    )
    # Raw data
    raw_data: Any | None = Field(
        default=None,
        description="Original finding data from the source system",
    )
    # Timestamps
    first_observed: datetime = Field(default_factory=utc_now)
    last_observed: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = Field(default=None)
