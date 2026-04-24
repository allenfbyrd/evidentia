"""Shared types, enums, and base classes used across all Evidentia models."""

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
    """Return the installed evidentia-core version.

    Used as a ``default_factory`` on report-stamp fields
    (``GapReport.evidentia_version`` etc.) so exported artifacts
    accurately record the version that produced them. Resolves via
    ``importlib.metadata`` — always matches the installed wheel.
    """
    from evidentia_core import __version__

    return __version__


class EvidentiaModel(BaseModel):
    """Base model for all Evidentia objects.

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
# ``evidentia_core.catalogs.manifest.load_manifest()``.


class OLIRRelationship(str, Enum):
    """NIST OLIR (Online Informative References) relationship types.

    Added in v0.7.0 to support enterprise-grade mapping claims. Rather
    than bare ``framework+control_id`` pairs, every :class:`ControlMapping`
    now declares the strength and direction of the relationship between
    the mapped evidence and the named control.

    Values match the NIST OLIR Derived Relationship Mapping (DRM)
    vocabulary at https://csrc.nist.gov/projects/olir/derived-relationship-mapping.
    An auditor reading evidence can tell the difference between
    "this finding fully evidences AC-6" (``SUBSET_OF``) and
    "this finding is loosely related to AC-6" (``RELATED_TO``).
    """

    EQUIVALENT_TO = "equivalent-to"
    """Evidence and control address the same objective via the same
    method. Functionally identical with identical outcomes."""

    EQUAL_TO = "equal-to"
    """Evidence and control are word-for-word identical. Rare between
    separate frameworks; common when mapping translations / re-issues."""

    SUBSET_OF = "subset-of"
    """Evidence is narrower than the control — addresses one specific
    aspect. The usual relationship between an automated finding and a
    NIST family control (e.g., 'S3 bucket is public' subset-of AC-3
    Access Enforcement)."""

    SUPERSET_OF = "superset-of"
    """Evidence is broader than the control. Uncommon in automated
    findings; typical for framework-to-framework crosswalks."""

    INTERSECTS_WITH = "intersects-with"
    """Evidence and control overlap but neither fully contains the
    other. Used when a finding partially evidences a control but also
    addresses things outside that control."""

    RELATED_TO = "related-to"
    """Weakest relationship: evidence and control share a topic but
    the mapping strength is unclassified. Default for pre-v0.7.0
    mappings that haven't been re-classified yet."""


class ControlMapping(EvidentiaModel):
    """Maps an entity (evidence, risk, gap) to a specific framework control.

    v0.7.0 extended the model with OLIR relationship typing and
    justification. Pre-v0.7.0 callers that constructed
    ``ControlMapping(framework=..., control_id=...)`` without the new
    fields continue to work — defaults (``relationship=RELATED_TO``,
    ``justification=""``) are supplied automatically. Collectors and
    mapping tables upgraded in v0.7.0 set explicit stronger relationships.
    """

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
    relationship: OLIRRelationship = Field(
        default=OLIRRelationship.RELATED_TO,
        description=(
            "NIST OLIR relationship type. v0.7.0+ mappings should declare "
            "the strongest honest relationship (typically ``SUBSET_OF`` "
            "for automated findings against family controls). Default "
            "``RELATED_TO`` preserves pre-v0.7.0 behaviour."
        ),
    )
    justification: str = Field(
        default="",
        max_length=1024,
        description=(
            "Free-text rationale for the mapping, typically citing the "
            "authoritative source (AWS Security Hub 'Related requirements', "
            "AWS Audit Manager framework entry, NIST OLIR submission, "
            "FedRAMP baseline appendix). Empty string = 'legacy mapping'."
        ),
    )

    def __str__(self) -> str:
        return f"{self.framework}:{self.control_id}"
