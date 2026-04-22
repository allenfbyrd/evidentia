"""Fetch the NIST SP 800-53 Rev 5 catalog + baseline profiles from usnistgov/oscal-content.

v0.2.1: this script is the authoritative way to regenerate the bundled
NIST catalog + 4 resolved baselines (Low, Moderate, High, Privacy). Run
it at release time against a pinned upstream tag for reproducibility.

Outputs (under ``packages/evidentia-core/src/evidentia_core/catalogs/data/us-federal/``):

- ``nist-800-53-rev5.json``           — full OSCAL catalog (dropped in as-is,
                                         loaded via ``load_oscal_catalog``)
- ``nist-800-53-rev5-low.json``       — resolved Low baseline (Evidentia format)
- ``nist-800-53-rev5-moderate.json``  — resolved Moderate baseline
- ``nist-800-53-rev5-high.json``      — resolved High baseline
- ``nist-800-53-rev5-privacy.json``   — resolved Privacy baseline

The four resolved baselines are produced by running the OSCAL profile
resolver (``evidentia_core.oscal.profile.resolve_profile``) against
each baseline profile JSON, then serializing via ``EvidentiaModel``.
Pre-resolving offline keeps the runtime install network-free.

Upstream: https://github.com/usnistgov/oscal-content (CC0 license)
"""

from __future__ import annotations

import json
import logging
import sys
import urllib.request
from pathlib import Path

# Pinned upstream version for reproducibility. Bump this tag when
# NIST releases updated content; re-run the script; commit the new
# JSONs. Don't use ``main`` — it's unstable.
UPSTREAM_TAG = "v1.4.0"

UPSTREAM_BASE = (
    f"https://raw.githubusercontent.com/usnistgov/oscal-content/{UPSTREAM_TAG}/"
    f"nist.gov/SP800-53/rev5/json/"
)

# (upstream_filename, local_slug, human_name)
CATALOG = ("NIST_SP-800-53_rev5_catalog.json", "nist-800-53-rev5", "NIST SP 800-53 Rev 5 (full)")
BASELINES = [
    ("NIST_SP-800-53_rev5_LOW-baseline_profile.json", "nist-800-53-rev5-low", "NIST SP 800-53 Rev 5 Low Baseline"),
    ("NIST_SP-800-53_rev5_MODERATE-baseline_profile.json", "nist-800-53-rev5-moderate", "NIST SP 800-53 Rev 5 Moderate Baseline"),
    ("NIST_SP-800-53_rev5_HIGH-baseline_profile.json", "nist-800-53-rev5-high", "NIST SP 800-53 Rev 5 High Baseline"),
    ("NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json", "nist-800-53-rev5-privacy", "NIST SP 800-53 Rev 5 Privacy Baseline"),
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = (
    REPO_ROOT
    / "packages"
    / "evidentia-core"
    / "src"
    / "evidentia_core"
    / "catalogs"
    / "data"
    / "us-federal"
)

logger = logging.getLogger("fetch_nist_oscal")


def _download(relpath: str) -> bytes:
    url = UPSTREAM_BASE + relpath
    logger.info("Downloading %s", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Evidentia/0.2.1 (release tooling)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310 — hardcoded https
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read()


def _write_json_preserving_shape(data: dict, out_path: Path) -> None:
    """Write JSON with 2-space indent and a trailing newline."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def fetch_full_catalog() -> Path:
    """Download the full NIST catalog OSCAL JSON verbatim.

    We don't transform it — our ``load_oscal_catalog`` already parses
    this shape directly. Keeping the upstream file byte-compatible makes
    future diff-review trivial.
    """
    raw = _download(CATALOG[0])
    data = json.loads(raw.decode("utf-8"))
    out_path = DATA_DIR / f"{CATALOG[1]}.json"
    _write_json_preserving_shape(data, out_path)
    # Control-count sanity print
    metadata = data.get("catalog", {}).get("metadata", {})
    groups = data.get("catalog", {}).get("groups", [])
    control_count = sum(
        len(g.get("controls", [])) + sum(
            len(c.get("controls", [])) for c in g.get("controls", [])
        )
        for g in groups
    )
    logger.info(
        "  → %s: %d top-level families, ~%d controls (incl. first-level enhancements), "
        "metadata.version=%s",
        out_path.name,
        len(groups),
        control_count,
        metadata.get("version"),
    )
    return out_path


def fetch_and_resolve_baseline(
    upstream_filename: str, slug: str, human_name: str
) -> Path:
    """Download a baseline profile JSON, resolve it, and write the catalog JSON.

    The resolved output uses our Evidentia JSON format (category=control,
    tier=A, placeholder=false) rather than the upstream OSCAL profile shape,
    because resolution flattens includes/excludes/set-parameters into a plain
    control list.

    Note: upstream profile ``back-matter.resources[].rlinks`` reference the
    catalog by its path *inside the usnistgov/oscal-content repo tree*
    (e.g., ``./NIST_SP-800-53_rev5_catalog.json``). Since we're resolving
    offline against our local copy, we rewrite each rlink ``href`` to point
    at the file we just fetched: ``nist-800-53-rev5.json`` in DATA_DIR.
    """
    # Stage the upstream profile to a temp file so our resolver can read it
    from tempfile import NamedTemporaryFile

    raw = _download(upstream_filename)
    profile_doc = json.loads(raw.decode("utf-8"))

    # Rewrite back-matter rlinks so `#<uuid>` resolves to our on-disk
    # full-catalog copy, not the upstream repo's relative path.
    back_matter = profile_doc.get("profile", {}).get("back-matter", {})
    rewrite_count = 0
    for resource in back_matter.get("resources", []):
        for rlink in resource.get("rlinks", []):
            original = rlink.get("href", "")
            # Only rewrite NIST 800-53 catalog references (be defensive —
            # profiles may reference other resources too).
            if "NIST_SP-800-53_rev5_catalog" in original:
                rlink["href"] = f"./{CATALOG[1]}.json"
                rewrite_count += 1
    logger.debug("  rewrote %d rlinks in %s", rewrite_count, upstream_filename)

    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
        dir=str(DATA_DIR),
    ) as tmp:
        json.dump(profile_doc, tmp)
        profile_path = Path(tmp.name)

    try:
        from evidentia_core.oscal.profile import resolve_profile

        resolved = resolve_profile(
            profile_path,
            override_framework_id=slug,
            override_framework_name=human_name,
        )

        # Serialize resolved catalog via the Evidentia model so the
        # on-disk file round-trips through our existing loaders.
        payload = {
            "framework_id": resolved.framework_id,
            "framework_name": resolved.framework_name,
            "version": resolved.version,
            "source": (
                f"usnistgov/oscal-content@{UPSTREAM_TAG} — "
                f"{upstream_filename} resolved against "
                f"NIST_SP-800-53_rev5_catalog.json (CC0 / U.S. Government work)"
            ),
            "tier": "A",
            "category": "control",
            "placeholder": False,
            "families": resolved.families,
            "controls": [
                c.model_dump(mode="json", exclude_none=True, by_alias=True)
                for c in resolved.controls
            ],
        }
        out_path = DATA_DIR / f"{slug}.json"
        _write_json_preserving_shape(payload, out_path)
        logger.info(
            "  → %s: %d top-level controls, families=%d",
            out_path.name,
            len(resolved.controls),
            len(resolved.families),
        )
        return out_path
    finally:
        profile_path.unlink(missing_ok=True)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger.info("Fetching NIST SP 800-53 Rev 5 from usnistgov/oscal-content@%s", UPSTREAM_TAG)
    logger.info("Target directory: %s", DATA_DIR)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    fetch_full_catalog()
    for upstream, slug, name in BASELINES:
        fetch_and_resolve_baseline(upstream, slug, name)

    logger.info("Done. Run `scripts/catalogs/regenerate_manifest.py` next to update frameworks.yaml.")


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT / "packages" / "evidentia-core" / "src"))
    main()
