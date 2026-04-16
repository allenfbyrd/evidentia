"""Generate US state privacy law catalogs — Tier D (state statutes, not copyrightable).

15 US state comprehensive privacy laws, plus the Virginia CDPA as a
canonical "VCDPA-family" reference. Each one is modeled as an
ObligationCatalog (not a ControlCatalog) because privacy statutes impose
obligations (subject rights, notice, applicability thresholds) rather
than implementable technical controls.

All are statutes enacted by US state legislatures and not copyrightable
(government edicts doctrine; Banks v. Manchester).
"""

from __future__ import annotations

from _generators import emit_obligation_catalog  # type: ignore[import-not-found]


# Common obligation template — each state has roughly these categories
# with jurisdiction-specific variations captured in the regime metadata.
COMMON_OBLIGATIONS_TEMPLATE = [
    ("ACCESS", "Right to access personal information", "subject-rights"),
    ("DELETE", "Right to delete personal information", "subject-rights"),
    ("CORRECT", "Right to correct inaccurate personal information", "subject-rights"),
    ("PORTABILITY", "Right to portability of personal information", "subject-rights"),
    ("OPT-OUT-SALE", "Right to opt out of sale of personal information", "subject-rights"),
    ("OPT-OUT-PROFILING", "Right to opt out of significant automated profiling", "subject-rights"),
    ("NOTICE", "Privacy notice / disclosure requirements at or before collection", "notice"),
    ("CONSENT-SENSITIVE", "Consent (or similar) required for processing sensitive data", "consent"),
    ("MINIMIZATION", "Purpose limitation and data minimization", "principles"),
    ("SECURITY", "Reasonable security practices to protect personal information", "security"),
    ("DPA-CONTRACT", "Contractual requirements for processors and service providers", "vendor"),
    ("DPA-ASSESSMENT", "Data protection impact assessment for high-risk processing", "accountability"),
    ("NON-DISCRIMINATION", "Prohibition on discrimination against consumers exercising rights", "subject-rights"),
]


def _obligations(state_prefix: str, overrides: dict | None = None) -> list[dict]:
    """Build a standard set of obligations for a state, with per-state ID prefixes."""
    overrides = overrides or {}
    out: list[dict] = []
    for suffix, title, cat in COMMON_OBLIGATIONS_TEMPLATE:
        if suffix in overrides.get("exclude", []):
            continue
        out.append({
            "id": f"{state_prefix}.{suffix}",
            "title": title,
            "description": title,
            "category": cat,
        })
    for extra in overrides.get("extras", []):
        out.append(extra)
    return out


# State definitions: (framework_id, name, citation, regime_overrides)
STATE_LAWS = [
    # California — CCPA as amended by CPRA
    {
        "framework_id": "us-ca-ccpa-cpra",
        "framework_name": "California Consumer Privacy Act / California Privacy Rights Act (CCPA/CPRA)",
        "version": "Cal. Civ. Code § 1798.100 et seq. (CCPA 2020; CPRA amendments 2023)",
        "source": "California Office of the Attorney General / California Privacy Protection Agency",
        "regime": {
            "jurisdiction": "US-CA",
            "effective_date": "2020-01-01",
            "amendments": ["CPRA 2023"],
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-sharing", "opt-out-profiling", "limit-sensitive", "non-discrimination"],
            "data_minimization_required": True,
            "dpia_required": True,
            "breach_notification_threshold_days": None,
            "private_right_of_action": True,
            "cure_period_days": None,
            "applicability_revenue_threshold_usd": 25_000_000,
            "applicability_record_threshold": 100_000,
            "applicability_revenue_share_from_data": 0.5,
            "regulator": "California Privacy Protection Agency (CPPA)",
        },
        "id_prefix": "CCPA",
    },
    # Virginia
    {
        "framework_id": "us-va-vcdpa",
        "framework_name": "Virginia Consumer Data Protection Act (VCDPA)",
        "version": "Va. Code § 59.1-575 et seq.",
        "source": "Virginia General Assembly",
        "regime": {
            "jurisdiction": "US-VA",
            "effective_date": "2023-01-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 30,
            "applicability_record_threshold": 100_000,
            "regulator": "Virginia Attorney General",
        },
        "id_prefix": "VCDPA",
    },
    # Colorado
    {
        "framework_id": "us-co-cpa",
        "framework_name": "Colorado Privacy Act (CPA)",
        "version": "Colo. Rev. Stat. § 6-1-1301 et seq.",
        "source": "Colorado General Assembly",
        "regime": {
            "jurisdiction": "US-CO",
            "effective_date": "2023-07-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 60,
            "applicability_record_threshold": 100_000,
            "regulator": "Colorado Attorney General",
        },
        "id_prefix": "COCPA",
    },
    # Connecticut
    {
        "framework_id": "us-ct-ctdpa",
        "framework_name": "Connecticut Data Privacy Act (CTDPA)",
        "version": "Conn. Gen. Stat. § 42-515 et seq.",
        "source": "Connecticut General Assembly",
        "regime": {
            "jurisdiction": "US-CT",
            "effective_date": "2023-07-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 60,
            "applicability_record_threshold": 100_000,
            "regulator": "Connecticut Attorney General",
        },
        "id_prefix": "CTDPA",
    },
    # Utah
    {
        "framework_id": "us-ut-ucpa",
        "framework_name": "Utah Consumer Privacy Act (UCPA)",
        "version": "Utah Code § 13-61 et seq.",
        "source": "Utah Legislature",
        "regime": {
            "jurisdiction": "US-UT",
            "effective_date": "2023-12-31",
            "subject_rights": ["access", "delete", "portability", "opt-out-sale"],
            "private_right_of_action": False,
            "cure_period_days": 30,
            "applicability_revenue_threshold_usd": 25_000_000,
            "applicability_record_threshold": 100_000,
            "regulator": "Utah Attorney General",
        },
        "id_prefix": "UCPA",
    },
    # Texas
    {
        "framework_id": "us-tx-tdpsa",
        "framework_name": "Texas Data Privacy and Security Act (TDPSA)",
        "version": "Tex. Bus. & Com. Code § 541 et seq.",
        "source": "Texas Legislature",
        "regime": {
            "jurisdiction": "US-TX",
            "effective_date": "2024-07-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 30,
            "regulator": "Texas Attorney General",
            "notes": "Applies to any company conducting business in Texas — no revenue or record thresholds.",
        },
        "id_prefix": "TDPSA",
    },
    # Oregon
    {
        "framework_id": "us-or-ocpa",
        "framework_name": "Oregon Consumer Privacy Act (OCPA)",
        "version": "Or. Rev. Stat. § 646A.570 et seq.",
        "source": "Oregon Legislature",
        "regime": {
            "jurisdiction": "US-OR",
            "effective_date": "2024-07-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 30,
            "applicability_record_threshold": 100_000,
            "regulator": "Oregon Attorney General",
        },
        "id_prefix": "OCPA",
    },
    # Delaware
    {
        "framework_id": "us-de-dpdpa",
        "framework_name": "Delaware Personal Data Privacy Act (DPDPA)",
        "version": "Del. Code tit. 6 § 12D-101 et seq.",
        "source": "Delaware General Assembly",
        "regime": {
            "jurisdiction": "US-DE",
            "effective_date": "2025-01-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "applicability_record_threshold": 35_000,
            "regulator": "Delaware Department of Justice",
        },
        "id_prefix": "DPDPA",
    },
    # Montana
    {
        "framework_id": "us-mt-mcdpa",
        "framework_name": "Montana Consumer Data Privacy Act (MCDPA)",
        "version": "Mont. Code § 30-14-2801 et seq.",
        "source": "Montana Legislature",
        "regime": {
            "jurisdiction": "US-MT",
            "effective_date": "2024-10-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "applicability_record_threshold": 50_000,
            "regulator": "Montana Attorney General",
        },
        "id_prefix": "MCDPA",
    },
    # Iowa
    {
        "framework_id": "us-ia-icdpa",
        "framework_name": "Iowa Consumer Data Protection Act (ICDPA)",
        "version": "Iowa Code § 715D et seq.",
        "source": "Iowa Legislature",
        "regime": {
            "jurisdiction": "US-IA",
            "effective_date": "2025-01-01",
            "subject_rights": ["access", "delete", "portability", "opt-out-sale"],
            "private_right_of_action": False,
            "cure_period_days": 90,
            "applicability_record_threshold": 100_000,
            "regulator": "Iowa Attorney General",
        },
        "id_prefix": "ICDPA",
    },
    # Florida — narrow applicability (big-tech targeted)
    {
        "framework_id": "us-fl-fdbr",
        "framework_name": "Florida Digital Bill of Rights (FDBR)",
        "version": "Fla. Stat. § 501.702 et seq.",
        "source": "Florida Legislature",
        "regime": {
            "jurisdiction": "US-FL",
            "effective_date": "2024-07-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "applicability_revenue_threshold_usd": 1_000_000_000,
            "regulator": "Florida Attorney General",
            "notes": "Narrow applicability — only businesses with $1B+ global revenue that derive 50%+ from online ad sales, operate app stores, or run smart speakers.",
        },
        "id_prefix": "FDBR",
    },
    # Tennessee
    {
        "framework_id": "us-tn-tipa",
        "framework_name": "Tennessee Information Protection Act (TIPA)",
        "version": "Tenn. Code § 47-18-3201 et seq.",
        "source": "Tennessee General Assembly",
        "regime": {
            "jurisdiction": "US-TN",
            "effective_date": "2025-07-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 60,
            "applicability_revenue_threshold_usd": 25_000_000,
            "applicability_record_threshold": 175_000,
            "regulator": "Tennessee Attorney General",
        },
        "id_prefix": "TIPA",
    },
    # New Hampshire
    {
        "framework_id": "us-nh-nhpa",
        "framework_name": "New Hampshire Privacy Act (NHPA)",
        "version": "NH Rev. Stat. § 507-H et seq.",
        "source": "New Hampshire General Court",
        "regime": {
            "jurisdiction": "US-NH",
            "effective_date": "2025-01-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 60,
            "applicability_record_threshold": 35_000,
            "regulator": "New Hampshire Attorney General",
        },
        "id_prefix": "NHPA",
    },
    # Maryland — strictest post-CCPA
    {
        "framework_id": "us-md-mdpa",
        "framework_name": "Maryland Online Data Privacy Act (MODPA)",
        "version": "Md. Code § 14-4601 et seq.",
        "source": "Maryland General Assembly",
        "regime": {
            "jurisdiction": "US-MD",
            "effective_date": "2025-10-01",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "data_minimization_required": True,
            "private_right_of_action": False,
            "applicability_record_threshold": 35_000,
            "regulator": "Maryland Attorney General",
            "notes": "MODPA has the strictest data-minimization standard among US state privacy laws as of 2025.",
        },
        "id_prefix": "MODPA",
    },
    # Minnesota
    {
        "framework_id": "us-mn-mncdpa",
        "framework_name": "Minnesota Consumer Data Privacy Act (MCDPA)",
        "version": "Minn. Stat. § 325O",
        "source": "Minnesota Legislature",
        "regime": {
            "jurisdiction": "US-MN",
            "effective_date": "2025-07-31",
            "subject_rights": ["access", "delete", "correct", "portability", "opt-out-sale", "opt-out-profiling", "appeal"],
            "dpia_required": True,
            "private_right_of_action": False,
            "cure_period_days": 30,
            "applicability_record_threshold": 100_000,
            "regulator": "Minnesota Attorney General",
        },
        "id_prefix": "MNCDPA",
    },
]


for state in STATE_LAWS:
    emit_obligation_catalog(
        framework_id=state["framework_id"],
        framework_name=state["framework_name"],
        version=state["version"],
        source=state["source"] + " (US state statute, not copyrightable under government edicts doctrine)",
        regime=state["regime"],
        obligations=_obligations(state["id_prefix"]),
        tier="D",
        subdir="state-privacy",
    )


if __name__ == "__main__":
    print(f"Generated {len(STATE_LAWS)} US state privacy law catalogs.")
