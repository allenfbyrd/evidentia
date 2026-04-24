"""Pydantic data models for Evidentia."""

from evidentia_core.models.catalog import (
    CatalogControl,
    ControlCatalog,
    CrosswalkDefinition,
    FrameworkMapping,
    RelationshipType,
)
from evidentia_core.models.common import (
    ControlMapping,
    EvidentiaModel,
    Severity,
    current_version,
    new_id,
    utc_now,
)
from evidentia_core.models.control import (
    ControlImplementation,
    ControlInventory,
    ControlStatus,
)
from evidentia_core.models.evidence import (
    EvidenceArtifact,
    EvidenceBundle,
    EvidenceSufficiency,
    EvidenceType,
)

# v0.7.0: evidentia_core.models.finding is NOT re-exported from this
# package root because it pulls in evidentia_core.audit.provenance,
# which itself depends on evidentia_core.models.common — eager re-export
# here creates a circular import when ``audit`` is loaded first (e.g.,
# by a collector). Callers should ``from evidentia_core.models.finding
# import SecurityFinding, FindingStatus`` directly. No production code
# used the convenience path before v0.7.0.
from evidentia_core.models.gap import (
    ControlGap,
    EfficiencyOpportunity,
    GapAnalysisReport,
    GapSeverity,
    GapStatus,
    ImplementationEffort,
)
from evidentia_core.models.obligation import (
    ObligationCatalog,
    PrivacyObligation,
    PrivacyRegime,
    SubjectRight,
)
from evidentia_core.models.risk import (
    ImpactRating,
    LikelihoodRating,
    RiskLevel,
    RiskRegister,
    RiskStatement,
    RiskTreatment,
)
from evidentia_core.models.threat import (
    AttackTechnique,
    TechniqueCatalog,
    ThreatCategory,
    Vulnerability,
    VulnerabilityCatalog,
)

# v0.3.0: ``FrameworkId`` removed (was deprecated in v0.2.0; the module-level
# ``__getattr__`` that emitted the DeprecationWarning is gone, and no
# production code references it — only the deprecation-warning test did,
# which has also been removed).

__all__ = [
    "AttackTechnique",
    "CatalogControl",
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
    "EvidentiaModel",
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
