#!/usr/bin/env python3
"""Deterministic regenerator for the 5 OSPS Baseline crosswalk JSONs.

The crosswalks at ``packages/evidentia-core/src/evidentia_core/catalogs/
data/mappings/osps-baseline_to_*.json`` are auto-extracted from the
OpenSSF OSPS Baseline ``baseline/OSPS-*.yaml`` family files at a pinned
upstream commit (see ``_osps_upstream.OSPS_BASELINE_COMMIT_SHA``). This
script reproduces those 5 JSONs **byte-for-byte** from the upstream YAML,
turning the previously hand-built artifacts into a reproducible build
output.

Why this exists
---------------
The pinned SHA + the per-mapping ``notes`` strings previously had to be
hand-swept across the 5 files (10-15 inline occurrences of the SHA alone)
on every upstream OSPS bump. With this regenerator, the next bump is:

1. Update ``OSPS_BASELINE_COMMIT_SHA`` in ``_osps_upstream.py``.
2. Run ``uv run python scripts/catalogs/gen_osps_crosswalks.py`` to
   regenerate all 5 JSONs from the new upstream revision.
3. Review the diff + commit.

The byte-for-byte fidelity was verified against the v0.10.6-shipped JSONs
(extracted at commit ``ac6bbec8...``): the upstream guidelines[] -> JSON
transform is lossless, with zero manual massaging.

Modes
-----
``gen_osps_crosswalks.py``
    Regenerate all 5 JSONs in place from the cached/fetched upstream YAML.
``gen_osps_crosswalks.py --check``
    Exit 0 if the regenerated output matches the committed JSONs
    byte-for-byte; exit 1 + print a per-file diff summary on drift.
    (CI / pre-tag drift gate.)
``gen_osps_crosswalks.py --output-dir DIR``
    Write to ``DIR`` instead of the in-tree mappings directory (useful
    for inspection).

Upstream fetch + cache
----------------------
Upstream YAML is fetched via the ``gh`` CLI and cached under
``.local/osps-upstream-<sha>/baseline/`` (``.local/`` is gitignored).
First run fetches + caches; subsequent runs reuse the cache. If the cache
is absent AND ``gh`` is unavailable, the script exits with a clear message
telling the operator how to populate the cache manually. Network-dependent
regeneration is acceptable for this dev-time tool.

Security note: every ``gh`` invocation uses ``subprocess.run`` with an
argument *list* (no shell), and the only interpolated values are the
pinned commit SHA (from ``_osps_upstream.py``) and a fixed
family-letter allowlist (:data:`OSPS_FAMILIES`) — no untrusted input
reaches the subprocess.

Per the publishing-authority protocol (~/.claude/CLAUDE.md), this script
NEVER pushes, tags, or publishes. It only fetches upstream + writes the
in-tree JSON artifacts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Repo-relative paths + the single-source upstream pin.
# ---------------------------------------------------------------------------

# scripts/catalogs/gen_osps_crosswalks.py -> repo root is three parents up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAPPINGS_DIR = (
    REPO_ROOT
    / "packages"
    / "evidentia-core"
    / "src"
    / "evidentia_core"
    / "catalogs"
    / "data"
    / "mappings"
)
# The constant module is co-located with the JSON artifacts it pins.
_OSPS_UPSTREAM_PATH = MAPPINGS_DIR / "_osps_upstream.py"


def _load_upstream_pin() -> tuple[str, str]:
    """Return ``(commit_sha, repo)`` from the co-located constant module.

    Read by executing ``_osps_upstream.py`` in a throwaway namespace
    rather than an ``import`` so the script works whether or not
    ``evidentia_core`` is installed in the running interpreter (it is a
    flat data-adjacent module with no package dependencies).
    """
    namespace: dict[str, Any] = {}
    exec(_OSPS_UPSTREAM_PATH.read_text(encoding="utf-8"), namespace)  # noqa: S102
    return namespace["OSPS_BASELINE_COMMIT_SHA"], namespace["OSPS_BASELINE_REPO"]


# ---------------------------------------------------------------------------
# Static extraction parameters (verified byte-for-byte against the
# v0.10.6-shipped JSONs).
# ---------------------------------------------------------------------------

# Upstream family files under ``baseline/`` whose controls carry the
# guidelines[] mappings. (Families with no entries for a given standard
# simply contribute nothing for that standard.)
OSPS_FAMILIES: tuple[str, ...] = (
    "AC",
    "BR",
    "DO",
    "GV",
    "LE",
    "QA",
    "SA",
    "VM",
)

SOURCE_FRAMEWORK = "osps-baseline-2026.02.19"
GENERATED_AT = "2026-05-27"
PROVENANCE = "upstream-osps-guidelines"
VERIFICATION = "self-attested-via-upstream"

# Map an upstream guideline ``reference-id`` (the standard key) to the
# shipped crosswalk's ``(target_framework slug, human display name)``.
# The slug is the JSON filename component (osps-baseline_to_<slug>.json);
# the display name is interpolated into ``version`` / ``verification_note``
# / each mapping's ``notes``.
STANDARD_TARGETS: dict[str, tuple[str, str]] = {
    "CRA": ("eu-cra", "EU Cyber Resilience Act"),
    "800-161": ("nist-800-161", "NIST SP 800-161"),
    "CSF": ("nist-csf-2.0", "NIST CSF 2.0"),
    "SSDF": ("nist-ssdf-800-218", "NIST SSDF SP 800-218"),
    "PCIDSS": ("pci-dss-4.0", "PCI DSS 4.0"),
}


# ---------------------------------------------------------------------------
# Pure functions (no I/O — unit-tested directly).
# ---------------------------------------------------------------------------


def extract_entries_by_standard(
    family_docs: dict[str, dict[str, Any]],
    standards: dict[str, tuple[str, str]] | None = None,
) -> dict[str, list[tuple[str, str, str]]]:
    """Extract per-standard ordered ``(control_id, title, target_id)`` tuples.

    ``family_docs`` maps a family code (``"AC"``) to its parsed
    ``OSPS-<fam>.yaml`` document. Iteration order is: family (in the order
    of ``family_docs``), then control (file order), then the standard's
    guideline block, then entry (file order) — exactly the order the
    v0.10.6 extraction preserved.

    Only standards present in ``standards`` (default
    :data:`STANDARD_TARGETS`) are collected; other guideline blocks
    (OpenCRE, PSSCRM, SLSA, ...) are ignored.

    Control titles are upstream YAML block scalars (``title: |``) and
    therefore carry a trailing newline; this strips surrounding
    whitespace to match the shipped ``source_control_title``. Entry IDs
    are likewise stripped (upstream has a few trailing-space artifacts,
    e.g. ``Claim 2.1.5   ``, that the shipped data already normalized).
    """
    if standards is None:
        standards = STANDARD_TARGETS
    out: dict[str, list[tuple[str, str, str]]] = {key: [] for key in standards}
    # Ordering contract: family_docs MUST be built in OSPS_FAMILIES order —
    # output byte-stability depends on iterating families in that fixed order.
    for doc in family_docs.values():
        for control in doc.get("controls") or []:
            control_id = str(control["id"]).strip()
            title = str(control["title"]).strip()
            for guideline in control.get("guidelines") or []:
                std_key = guideline.get("reference-id")
                if std_key not in standards:
                    continue
                for entry in guideline.get("entries") or []:
                    entry_id = entry.get("reference-id")
                    if entry_id is None:
                        continue
                    out[std_key].append((control_id, title, str(entry_id).strip()))
    return out


def build_mapping(control_id: str, title: str, target_id: str, display: str) -> dict[str, str]:
    """Build a single ``mappings[]`` entry (stable field order)."""
    return {
        "source_control_id": control_id,
        "source_control_title": title,
        "target_control_id": target_id,
        "target_control_title": "",
        "relationship": "related",
        "notes": (
            f"Auto-extracted from upstream {control_id} guidelines[]; "
            f"verify against {display} before relying on for audit."
        ),
    }


def build_crosswalk(
    slug: str,
    display: str,
    entries: list[tuple[str, str, str]],
    commit_sha: str,
) -> dict[str, Any]:
    """Build the full crosswalk payload dict for one target framework.

    The top-level field order matches the shipped JSONs exactly
    (source_framework, target_framework, version, generated_at, source,
    provenance, verification, verification_note, mappings).
    """
    return {
        "source_framework": SOURCE_FRAMEWORK,
        "target_framework": slug,
        "version": f"OSPS Baseline v2026.02.19 / {display}",
        "generated_at": GENERATED_AT,
        "source": (
            "Auto-extracted from OpenSSF OSPS Baseline guidelines[] array "
            f"at upstream commit {commit_sha}"
        ),
        "provenance": PROVENANCE,
        "verification": VERIFICATION,
        "verification_note": (
            "Mappings auto-extracted from the OpenSSF OSPS Baseline "
            f"guidelines[] array at upstream commit {commit_sha}. Not "
            f"independently verified against {display}. Consumers requiring "
            "independent verification should plan a hand-check pass."
        ),
        "mappings": [
            build_mapping(control_id, title, target_id, display)
            for control_id, title, target_id in entries
        ],
    }


def serialize(payload: dict[str, Any]) -> str:
    """Serialize a crosswalk payload to the shipped on-disk byte form.

    ``indent=2`` + ``ensure_ascii=False`` + a single trailing newline —
    verified byte-for-byte against all 5 v0.10.6-shipped JSONs.
    """
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def build_all_crosswalks(
    family_docs: dict[str, dict[str, Any]],
    commit_sha: str,
    standards: dict[str, tuple[str, str]] | None = None,
) -> dict[str, str]:
    """Build every crosswalk; return ``{filename: serialized_json}``."""
    if standards is None:
        standards = STANDARD_TARGETS
    by_std = extract_entries_by_standard(family_docs, standards)
    result: dict[str, str] = {}
    for std_key, (slug, display) in standards.items():
        payload = build_crosswalk(slug, display, by_std[std_key], commit_sha)
        result[f"osps-baseline_to_{slug}.json"] = serialize(payload)
    return result


# ---------------------------------------------------------------------------
# I/O: upstream fetch + cache.
# ---------------------------------------------------------------------------


def cache_dir_for(commit_sha: str) -> Path:
    """Return the ``.local/`` cache directory for a given upstream SHA."""
    return REPO_ROOT / ".local" / f"osps-upstream-{commit_sha}" / "baseline"


def fetch_family_yaml(repo: str, commit_sha: str, family: str) -> str:
    """Fetch one ``baseline/OSPS-<family>.yaml`` via the ``gh`` CLI (raw).

    Uses an argument list (no shell). ``repo`` / ``commit_sha`` / ``family``
    are constants from the pinned config + the fixed family allowlist.
    """
    proc = subprocess.run(
        [
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github.raw+json",
            f"repos/{repo}/contents/baseline/OSPS-{family}.yaml?ref={commit_sha}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh api failed for OSPS-{family}.yaml (exit {proc.returncode}): "
            f"{proc.stderr.strip()[:400]}"
        )
    return proc.stdout


def load_family_docs(
    commit_sha: str,
    repo: str,
    *,
    allow_fetch: bool = True,
) -> dict[str, dict[str, Any]]:
    """Load + parse all upstream family YAMLs, fetching + caching as needed.

    Returns ``{family_code: parsed_yaml_doc}`` in :data:`OSPS_FAMILIES`
    order. On a cache miss, fetches via the ``gh`` CLI (when ``allow_fetch``)
    and writes the raw YAML into the gitignored cache. If a file is
    missing AND fetching is disabled / ``gh`` is unavailable, raises with
    operator guidance.
    """
    cache = cache_dir_for(commit_sha)
    docs: dict[str, dict[str, Any]] = {}
    gh_available: bool | None = None
    for family in OSPS_FAMILIES:
        path = cache / f"OSPS-{family}.yaml"
        if not path.exists():
            if not allow_fetch:
                raise FileNotFoundError(_missing_cache_message(cache, family))
            if gh_available is None:
                gh_available = _gh_available()
            if not gh_available:
                raise FileNotFoundError(_missing_cache_message(cache, family))
            raw = fetch_family_yaml(repo, commit_sha, family)
            cache.mkdir(parents=True, exist_ok=True)
            path.write_text(raw, encoding="utf-8")
        docs[family] = yaml.safe_load(path.read_text(encoding="utf-8"))
    # Ordering contract (byte-stability): docs is built by iterating
    # OSPS_FAMILIES, so its key order equals OSPS_FAMILIES. The downstream
    # extractor relies on this — guard it here cheaply rather than trust it.
    assert list(docs) == list(OSPS_FAMILIES)
    return docs


def _gh_available() -> bool:
    """True if the ``gh`` CLI is invocable."""
    try:
        proc = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return False
    return proc.returncode == 0


def _missing_cache_message(cache: Path, family: str) -> str:
    return (
        f"Upstream cache miss: {cache / f'OSPS-{family}.yaml'} not found and "
        "gh is unavailable (or fetching disabled).\n"
        "Populate the cache manually, e.g.:\n"
        f"  mkdir -p '{cache}'\n"
        "  for f in AC BR DO GV LE QA SA VM; do\n"
        "    gh api -H 'Accept: application/vnd.github.raw+json' \\\n"
        "      'repos/<repo>/contents/baseline/OSPS-'$f'.yaml?ref=<sha>' \\\n"
        f"      > '{cache}/OSPS-'$f'.yaml'\n"
        "  done\n"
        "(<repo> + <sha> come from _osps_upstream.py.)"
    )


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _diff_summary(expected: str, actual: str, name: str) -> str:
    """Return a short first-divergence summary between two text blobs."""
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    for i, (exp, act) in enumerate(zip(exp_lines, act_lines)):
        if exp != act:
            return (
                f"  {name}: first diff at line {i + 1}\n"
                f"    committed:   {exp!r}\n"
                f"    regenerated: {act!r}"
            )
    if len(exp_lines) != len(act_lines):
        return (
            f"  {name}: line-count differs "
            f"(committed={len(exp_lines)}, regenerated={len(act_lines)})"
        )
    # Same lines but different bytes (trailing-newline / EOL difference).
    return f"  {name}: content differs only in trailing bytes / EOL"


def _compare(regenerated: dict[str, str], committed_dir: Path) -> list[str]:
    """Compare regenerated crosswalk bytes against the committed copies.

    ``regenerated`` is ``{filename: serialized_json}`` (the output of
    :func:`build_all_crosswalks`). Returns an ordered list of per-file
    drift summaries (one entry per drifted/missing file); an empty list
    means every regenerated file matches its committed copy byte-for-byte.

    Pure (no network, no writes): only reads the committed files under
    ``committed_dir``. This is the comparison the ``--check`` CLI mode
    builds on.
    """
    drift: list[str] = []
    for name, content in sorted(regenerated.items()):
        committed_path = committed_dir / name
        if not committed_path.exists():
            drift.append(f"  {name}: committed file missing")
            continue
        committed = committed_path.read_text(encoding="utf-8")
        if committed != content:
            drift.append(_diff_summary(committed, content, name))
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not write. Exit 0 if regenerated output matches the "
            "committed JSONs byte-for-byte; exit 1 + print a diff summary "
            "on drift."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=MAPPINGS_DIR,
        help=(
            "Directory to write JSONs into (default: the in-tree mappings "
            "dir). Ignored under --check, which always compares against the "
            "in-tree committed files."
        ),
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help=(
            "Never invoke gh; rely solely on the .local cache. Fails with "
            "operator guidance on a cache miss."
        ),
    )
    args = parser.parse_args(argv)

    commit_sha, repo = _load_upstream_pin()
    try:
        family_docs = load_family_docs(
            commit_sha, repo, allow_fetch=not args.no_fetch
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    generated = build_all_crosswalks(family_docs, commit_sha)

    if args.check:
        # --check always compares against the in-tree committed files.
        drift = _compare(generated, MAPPINGS_DIR)
        if drift:
            print(
                "DRIFT: regenerated OSPS crosswalks differ from committed:",
                file=sys.stderr,
            )
            for line in drift:
                print(line, file=sys.stderr)
            print(
                "\nRe-run without --check to regenerate, or reconcile the "
                "upstream pin in _osps_upstream.py.",
                file=sys.stderr,
            )
            return 1
        print(f"OK: all {len(generated)} OSPS crosswalks match committed bytes.")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in sorted(generated.items()):
        (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"  wrote {args.output_dir / name}")
    print(
        f"Regenerated {len(generated)} OSPS crosswalks "
        f"from {repo}@{commit_sha[:12]}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
