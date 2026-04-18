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


def current_version() -> str:
    """Return the installed controlbridge-core version.

    Used as a ``default_factory`` on report-stamp fields
    (``GapReport.controlbridge_version`` etc.) so exported artifacts
    accurately record the version that produced them. Resolves via
    ``importlib.metadata`` — always matches the installed wheel.
    """
    from controlbridge_core import __version__

    return __version__


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


# v0.3.0: ``FrameworkId`` enum REMOVED per the v0.2.0 deprecation notice.
# v0.1.x shipped a 2-value enum (NIST_800_53_MOD + SOC2_TSC); v0.2.0 kept it
# behind a DeprecationWarning-emitting module ``__getattr__``; v0.3.0 drops
# it entirely. Use plain string framework IDs — ``ControlMapping.framework``
# has always been ``str``, so no caller was type-dependent on the enum.
# For the canonical list of bundled framework IDs, use
# ``controlbridge_core.catalogs.manifest.load_manifest()``.


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
