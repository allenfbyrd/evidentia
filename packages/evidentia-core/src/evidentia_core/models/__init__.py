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
from evidentia_core.models.finding import (
    FindingStatus,
    SecurityFinding,
)
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
    "FindingStatus",
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
