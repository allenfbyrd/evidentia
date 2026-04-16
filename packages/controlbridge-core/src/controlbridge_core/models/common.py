"""Shared types, enums, and base classes used across all ControlBridge models."""

from __future__ import annotations

import warnings
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


class _FrameworkIdImpl(str, Enum):
    """Canonical framework identifiers (DEPRECATED in v0.2.0).

    .. deprecated:: 0.2.0
        The enum-based framework ID approach cannot scale to the ~50
        bundled frameworks introduced in v0.2.0. Use the string-valued
        framework IDs from the manifest-driven registry instead:
        :func:`controlbridge_core.catalogs.manifest.load_manifest`.
        This enum will be removed in v0.3.0.

    Note: ``ControlMapping.framework`` already uses free-form ``str``,
    so any framework ID can be used in mappings regardless of this enum.
    """

    NIST_800_53_MOD = "nist-800-53-mod"
    SOC2_TSC = "soc2-tsc"


def __getattr__(name: str) -> object:
    """Emit a DeprecationWarning when ``FrameworkId`` is imported.

    Python only consults module-level ``__getattr__`` when normal
    attribute lookup fails — so we deliberately do **not** bind
    ``FrameworkId`` at module scope. The implementation lives under
    ``_FrameworkIdImpl``; public access goes through here so every
    ``from ... import FrameworkId`` triggers the warning exactly once
    per ``warnings`` filter.
    """
    if name == "FrameworkId":
        warnings.warn(
            "controlbridge_core.models.common.FrameworkId is deprecated in "
            "v0.2.0 and will be removed in v0.3.0. Use "
            "controlbridge_core.catalogs.manifest.load_manifest() for the "
            "authoritative list of bundled frameworks, and plain string "
            "framework IDs (e.g., 'nist-800-53-mod') in ControlMapping.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _FrameworkIdImpl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
