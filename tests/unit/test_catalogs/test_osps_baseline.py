"""Catalog-load smoke tests for the OSPS Baseline 3-maturity bundle.

v0.10.6 P1 (commit C1) — first OpenSSF OSPS Baseline catalog ship.

The OSPS Baseline (`ossf/security-baseline`, Apache-2.0, pinned at
commit ``ac6bbec`` for this bundle) declares 41 top-level controls
across 8 families (AC, BR, DO, GV, LE, QA, SA, VM) and 65 underlying
assessment-requirements. Each requirement carries an upstream
``applicability:`` list naming the maturity levels (1, 2, 3) at which
it applies.

Evidentia bundles the requirements (not the top-level controls) as
the catalog entries, because each requirement is the testable
conformance atom — this matches the v0.10.5 plan precedent of
treating ``OSPS-AC-04.01`` / ``OSPS-AC-04.02`` as separately
declarable items.

Counts verified against upstream tarball at commit ``ac6bbec``:

  - M1: 25 requirements (applicability includes ``maturity-1``)
  - M2: 42 requirements (applicability includes ``maturity-2``)
  - M3: 63 requirements (applicability includes ``maturity-3``)

NOTE: the v0.10.6 plan §Phase 1 cited 21/38/58. Those numbers do not
match the upstream tarball at the pinned SHA. The actual upstream
counts (25/42/63) are used here — see the commit body + the v0.10.6
plan corrections-log for the drift rationale.
"""

from __future__ import annotations

import json
from pathlib import Path

from evidentia_core.catalogs.loader import load_evidentia_catalog

CATALOG_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "packages"
    / "evidentia-core"
    / "src"
    / "evidentia_core"
    / "catalogs"
    / "data"
    / "international"
)


def test_osps_baseline_m1_loads_with_25_requirements() -> None:
    """M1 catalog loads + exposes 25 assessment-requirements."""
    catalog = load_evidentia_catalog(CATALOG_DIR / "osps-baseline-m1.yaml")
    assert catalog.framework_id == "osps-baseline-m1"
    assert len(catalog.controls) == 25


def test_osps_baseline_m2_loads_with_42_requirements() -> None:
    """M2 catalog loads + exposes 42 assessment-requirements."""
    catalog = load_evidentia_catalog(CATALOG_DIR / "osps-baseline-m2.yaml")
    assert catalog.framework_id == "osps-baseline-m2"
    assert len(catalog.controls) == 42


def test_osps_baseline_m3_loads_with_63_requirements() -> None:
    """M3 catalog loads + exposes 63 assessment-requirements."""
    catalog = load_evidentia_catalog(CATALOG_DIR / "osps-baseline-m3.yaml")
    assert catalog.framework_id == "osps-baseline-m3"
    assert len(catalog.controls) == 63


def test_osps_baseline_m1_subset_of_m2_subset_of_m3() -> None:
    """Maturity is mostly additive — every M1 req that is also M2/M3
    must appear in those catalogs.

    Upstream has 2 known exceptions where a requirement applies at
    M1 only and is intentionally dropped at higher maturity levels
    (``OSPS-BR-07.01``, ``OSPS-VM-02.01``). We preserve that fidelity
    rather than papering over the upstream gap.
    """
    m1 = load_evidentia_catalog(CATALOG_DIR / "osps-baseline-m1.yaml")
    m2 = load_evidentia_catalog(CATALOG_DIR / "osps-baseline-m2.yaml")
    m3 = load_evidentia_catalog(CATALOG_DIR / "osps-baseline-m3.yaml")

    m1_ids = {c.id for c in m1.controls}
    m2_ids = {c.id for c in m2.controls}
    m3_ids = {c.id for c in m3.controls}

    # Upstream-documented exceptions to additivity.
    KNOWN_M1_ONLY = {"OSPS-BR-07.01", "OSPS-VM-02.01"}

    # Every M1 req EXCEPT the upstream-documented exceptions must show
    # up at M2 and M3.
    assert (m1_ids - KNOWN_M1_ONLY).issubset(m2_ids)
    assert (m1_ids - KNOWN_M1_ONLY).issubset(m3_ids)
    # Every M2 req must show up at M3 (no known M2-only exceptions
    # in upstream at the pinned SHA).
    assert m2_ids.issubset(m3_ids)


def test_osps_baseline_tier_a_apache_license() -> None:
    """OSPS Baseline ships Tier-A — Apache-2.0 redistributable.

    Verifies all 3 catalogs declare ``tier: A`` and reference the
    upstream Apache-2.0 license in the ``source`` field.
    """
    for level in ("m1", "m2", "m3"):
        catalog = load_evidentia_catalog(CATALOG_DIR / f"osps-baseline-{level}.yaml")
        assert catalog.tier == "A", f"osps-baseline-{level} must be Tier-A"
        assert not catalog.placeholder, f"osps-baseline-{level} ships full content, not a placeholder"
        assert "Apache" in (catalog.license_terms or ""), f"osps-baseline-{level} must carry Apache-2.0 license_terms"


def test_osps_baseline_oscal_validates_against_schema() -> None:
    """OSCAL Catalog conversion validates against NIST OSCAL 1.2.1 shape.

    Asserts: top-level ``catalog`` object, stable UUID, ``oscal-version``
    metadata field set to ``1.2.1``, 41 total controls across the 8 OSPS
    families (the top-level controls — *not* the 65 assessment
    requirements; the OSCAL serialization mirrors the upstream
    top-level-control granularity per the OSCAL-Catalog convention).
    """
    oscal_path = CATALOG_DIR / "osps-baseline.oscal.json"
    with oscal_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "catalog" in data
    assert "uuid" in data["catalog"]
    assert "metadata" in data["catalog"]
    assert data["catalog"]["metadata"]["oscal-version"] == "1.2.1"
    groups = data["catalog"].get("groups", [])
    assert len(groups) == 8, f"Expected 8 OSPS families, got {len(groups)}"
    total_controls = sum(len(g.get("controls", [])) for g in groups)
    assert total_controls == 41, f"Expected 41 OSPS controls, got {total_controls}"
