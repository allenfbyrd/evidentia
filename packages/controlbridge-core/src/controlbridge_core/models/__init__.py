"""Pydantic data models for ControlBridge."""

from controlbridge_core.models.catalog import (
    CatalogControl,
    ControlCatalog,
    CrosswalkDefinition,
    FrameworkMapping,
    RelationshipType,
)
from controlbridge_core.models.common import (
    ControlBridgeModel,
    ControlMapping,
    Severity,
    current_version,
    new_id,
    utc_now,
)

# FrameworkId is deprecated in v0.2.0 — access it through the
# module that owns it; importing it from the package re-export would
# trigger the DeprecationWarning during package init on every import.
# Kept in __all__ for discoverability; users get the warning when they
# actually reference it.


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name == "FrameworkId":
        from controlbridge_core.models.common import (  # noqa: F401
            FrameworkId as _FI,
        )

        return _FI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
from controlbridge_core.models.control import (
    ControlImplementation,
    ControlInventory,
    ControlStatus,
)
from controlbridge_core.models.evidence import (
    EvidenceArtifact,
    EvidenceBundle,
    EvidenceSufficiency,
    EvidenceType,
)
from controlbridge_core.models.finding import (
    FindingStatus,
    SecurityFinding,
)
from controlbridge_core.models.gap import (
    ControlGap,
    EfficiencyOpportunity,
    GapAnalysisReport,
    GapSeverity,
    GapStatus,
    ImplementationEffort,
)
from controlbridge_core.models.obligation import (
    ObligationCatalog,
    PrivacyObligation,
    PrivacyRegime,
    SubjectRight,
)
from controlbridge_core.models.risk import (
    ImpactRating,
    LikelihoodRating,
    RiskLevel,
    RiskRegister,
    RiskStatement,
    RiskTreatment,
)
from controlbridge_core.models.threat import (
    AttackTechnique,
    TechniqueCatalog,
    ThreatCategory,
    Vulnerability,
    VulnerabilityCatalog,
)

__all__ = [
    "AttackTechnique",
    "CatalogControl",
    "ControlBridgeModel",
    "ControlCatalog",
    "ControlGap",
    "ControlImplementation",
    "ControlInventory",
    "ControlMapping",
    "ControlStatus",
    "CrosswalkDefinition",
    "EfficiencyOpportunity",
    "EvidenceArtifact",
    "EvidenceBundle",
    "EvidenceSufficiency",
    "EvidenceType",
    "FindingStatus",
    "FrameworkId",
    "FrameworkMapping",
    "GapAnalysisReport",
    "GapSeverity",
    "GapStatus",
    "ImpactRating",
    "ImplementationEffort",
    "LikelihoodRating",
    "ObligationCatalog",
    "PrivacyObligation",
    "PrivacyRegime",
    "RelationshipType",
    "RiskLevel",
    "RiskRegister",
    "RiskStatement",
    "RiskTreatment",
    "SecurityFinding",
    "Severity",
    "SubjectRight",
    "TechniqueCatalog",
    "ThreatCategory",
    "Vulnerability",
    "VulnerabilityCatalog",
    "current_version",
    "new_id",
    "utc_now",
]
