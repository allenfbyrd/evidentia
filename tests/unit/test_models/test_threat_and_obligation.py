"""Smoke tests for v0.2.0 threat and obligation models."""

from __future__ import annotations

from controlbridge_core.models.obligation import (
    ObligationCatalog,
    PrivacyObligation,
    PrivacyRegime,
)
from controlbridge_core.models.threat import (
    AttackTechnique,
    TechniqueCatalog,
    Vulnerability,
    VulnerabilityCatalog,
)


def test_attack_technique_minimal() -> None:
    tech = AttackTechnique(
        id="T1078",
        name="Valid Accounts",
        description="Adversaries may obtain and abuse credentials of existing accounts...",
        tactic_names=["Initial Access", "Persistence"],
    )
    assert tech.id == "T1078"
    assert "Initial Access" in tech.tactic_names
    assert tech.is_subtechnique is False


def test_technique_catalog_indexing() -> None:
    catalog = TechniqueCatalog(
        framework_id="mitre-attack-enterprise",
        framework_name="MITRE ATT&CK Enterprise",
        version="v15.1",
        source="https://attack.mitre.org",
        techniques=[
            AttackTechnique(
                id="T1078",
                name="Valid Accounts",
                description="...",
                tactic_names=["Initial Access"],
            ),
            AttackTechnique(
                id="T1078.001",
                name="Default Accounts",
                description="...",
                is_subtechnique=True,
                parent_technique_id="T1078",
                tactic_names=["Initial Access"],
            ),
        ],
    )
    assert catalog.get_technique("T1078") is not None
    assert catalog.get_technique("T1078.001") is not None
    assert catalog.technique_count == 2
    assert len(catalog.by_tactic("Initial Access")) == 2


def test_vulnerability_catalog_indexing() -> None:
    catalog = VulnerabilityCatalog(
        framework_id="cisa-kev",
        framework_name="CISA Known Exploited Vulnerabilities",
        version="2024-01-01",
        source="https://cisa.gov/kev",
        vulnerabilities=[
            Vulnerability(
                cve_id="CVE-2024-12345",
                vendor="ExampleCorp",
                product="ExampleProduct",
                description="Remote code execution via...",
                required_action="Apply vendor patch by due date",
                known_ransomware_use=True,
            )
        ],
    )
    cve = catalog.get_vulnerability("CVE-2024-12345")
    assert cve is not None
    assert cve.known_ransomware_use is True
    assert catalog.vulnerability_count == 1


def test_obligation_catalog_indexing() -> None:
    regime = PrivacyRegime(
        jurisdiction="US-CA",
        effective_date="2020-01-01",
        subject_rights=["access", "delete", "opt-out-sale"],
        private_right_of_action=True,
        breach_notification_threshold_days=None,
    )
    catalog = ObligationCatalog(
        framework_id="us-ca-ccpa-cpra",
        framework_name="California CCPA/CPRA",
        version="2023",
        source="Cal. Civ. Code § 1798.100 et seq.",
        regime=regime,
        obligations=[
            PrivacyObligation(
                id="CCPA.ACCESS",
                title="Right to know / access",
                description="Consumers have the right to know what personal information...",
                category="subject-rights",
                citation="Cal. Civ. Code § 1798.100",
            ),
            PrivacyObligation(
                id="CCPA.DELETE",
                title="Right to delete",
                description="...",
                category="subject-rights",
                citation="Cal. Civ. Code § 1798.105",
            ),
        ],
    )
    assert catalog.get_obligation("CCPA.ACCESS") is not None
    assert catalog.obligation_count == 2
    subject_rights = catalog.by_category("subject-rights")
    assert len(subject_rights) == 2
    assert catalog.regime.private_right_of_action is True
