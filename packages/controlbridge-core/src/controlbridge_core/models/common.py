"""Shared types, enums, and base classes used across all ControlBridge models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(UTC)


def new_id() -> str:
    """Generate a new UUID v4 string."""
    return str(uuid4())


class ControlBridgeModel(BaseModel):
    """Base model for all ControlBridge objects.

    Provides consistent serialization settings:
    - Enums serialize to their string values
    - Datetimes serialize to ISO 8601
    - Extra fields are forbidden (strict schema)
    - Whitespace is stripped from strings on input
    """

    model_config = ConfigDict(
        use_enum_values=True,
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class Severity(str, Enum):
    """Universal severity levels used across gaps, risks, and findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FrameworkId(str, Enum):
    """Canonical framework identifiers used throughout ControlBridge."""

    NIST_800_53_REV5 = "nist-800-53-rev5"
    NIST_800_53_MOD = "nist-800-53-mod"
    NIST_800_53_HIGH = "nist-800-53-high"
    NIST_CSF_2 = "nist-csf-2.0"
    SOC2_TSC = "soc2-tsc"
    ISO_27001_2022 = "iso27001-2022"
    CIS_CONTROLS_V8 = "cis-controls-v8"
    CMMC_2_LEVEL2 = "cmmc-2-level2"
    PCI_DSS_4 = "pci-dss-4"


class ControlMapping(ControlBridgeModel):
    """Maps an entity (evidence, risk, gap) to a specific framework control."""

    framework: str = Field(
        description="Framework identifier, e.g. 'nist-800-53-rev5', 'soc2-tsc'"
    )
    control_id: str = Field(
        description="Control identifier within the framework, e.g. 'AC-2', 'CC6.1'"
    )
    control_title: str | None = Field(
        default=None,
        description="Human-readable control title",
    )

    def __str__(self) -> str:
        return f"{self.framework}:{self.control_id}"
