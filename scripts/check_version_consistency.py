#!/usr/bin/env python3
"""Pre-push / pre-tag gate: the "never-skip-a-version-reference" safeguard.

Evidentia v0.10.7 Phase E4. Reads the declarative manifest
``scripts/version_tracked_files.yaml`` (the SAME file
``scripts/bump_version.py`` drives its replacements from) and enforces two
invariants against the working tree / HEAD:

  1. COVERAGE — every ``tracked`` file actually holds the CURRENT project
     version where the entry's ``kind`` expects it. Catches a file that was
     supposed to be bumped but was skipped (e.g. the README container tag
     drifting to a stale ``v0.10.6`` while everything else moved to 0.10.7).

  2. NEVER-SKIP — grep EVERY git-tracked file for a project-version literal
     (the ``0.7.x``..``0.99.x`` family, optionally ``v``-prefixed). Any file
     that contains such a literal yet is in NEITHER ``tracked`` NOR
     ``frozen`` is a HARD FAIL: a new version reference appeared that nobody
     classified, so the next bump would silently skip it.

The "current version" source of truth is
``packages/evidentia-core/pyproject.toml``'s ``version`` field — the same
detector the bumper uses.

The per-``kind`` COVERAGE patterns are obtained from
``bump_version.replacements_for_kind`` (the regex half of each
(regex, replacement) pair matches the version it is searching for), so the
gate and the bumper can never use divergent patterns.

Exit codes:
    0 — PASS (coverage holds + no unclassified literal)
    1 — FAIL (a tracked file is stale, OR an unclassified literal exists)
    2 — usage / IO error

Usage:
    python scripts/check_version_consistency.py
    python scripts/check_version_consistency.py --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
BUMP_VERSION_PATH = SCRIPTS_DIR / "bump_version.py"

# The project-version family. Evidentia ships ``0.7.x`` .. ``0.x`` (pre-1.0),
# optionally written ``vX.Y.Z`` (tag form) and occasionally with a 4th
# hot-fix segment (``X.Y.Z.W``). The leading ``(?<![\w.])`` / trailing
# ``(?![\w])`` guards stop matches inside longer numbers or identifiers.
# The minor is restricted to >= 7 so the swarm of small third-party
# dependency versions (``0.1.x`` .. ``0.6.x``) does NOT inflate the gate;
# in-range coincidental dep versions live in ``frozen`` trees (lockfiles,
# src docstrings) anyway.
PROJECT_VERSION_RE = re.compile(
    r"(?<![\w.])v?0\.(?:[7-9]|[1-9][0-9])\.\d+(?:\.\d+)?(?![\w])"
)

# COVERAGE is hard-asserted only for kinds whose literal is ALWAYS present
# at the current version. The others are advisory:
#   - workspace_pins  : a file may legitimately carry no workspace pins
#                       (evidentia-core depends on no sibling).
#   - pip_extra_pin   : docker/requirements.in tracks the last *published*
#                       release (lags the in-prep bump by design); the
#                       Dockerfile carries no such literal at all.
#   - cff_date        : a date, not the version.
_COVERAGE_REQUIRED_KINDS = {
    "python_version",
    "json_version",
    "cff_version",
    "readme_container_tag",
}


def _load_bump_module() -> Any:
    """Import scripts/bump_version.py as a module (no __init__.py)."""
    spec = importlib.util.spec_from_file_location(
        "bump_version_for_consistency", BUMP_VERSION_PATH
    )
    if spec is None or spec.loader is None:  # pragma: no cover - import guard
        sys.exit("Cannot import scripts/bump_version.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def coverage_pattern(bump: Any, kind: str, current: str) -> re.Pattern[str] | None:
    """Return the regex that matches the CURRENT version literal for ``kind``.

    Reuses the bumper's own pattern (the regex half of the first
    (regex, replacement) pair produced for current->current) so the gate and
    the bumper never diverge. Returns None when the kind produces no pattern
    (e.g. workspace_pins with an empty allowlist).
    """
    pairs = bump.replacements_for_kind(
        kind, current, current, packages=bump.workspace_packages(), bump_date="0000-00-00"
    )
    if not pairs:
        return None
    return re.compile(pairs[0][0])


def check_coverage(bump: Any, manifest: dict[str, list[dict[str, str]]], current: str) -> list[str]:
    """Verify every tracked file holds the current version where expected.

    Returns a list of human-readable failure strings (empty == pass).
    """
    failures: list[str] = []
    all_tracked = bump.tracked_files()
    for entry in manifest["tracked"]:
        spec = entry["path"]
        kind = entry["kind"]
        if kind not in _COVERAGE_REQUIRED_KINDS:
            continue
        pattern = coverage_pattern(bump, kind, current)
        if pattern is None:
            continue
        matched_files = bump.expand_manifest_path(spec, all_tracked)
        if not matched_files:
            failures.append(
                f"tracked entry '{spec}' (kind={kind}) matched no git-tracked "
                f"file — fix the path/glob in scripts/version_tracked_files.yaml"
            )
            continue
        for p in matched_files:
            try:
                text = p.read_text(encoding="utf-8")
            except OSError as exc:
                failures.append(f"cannot read tracked file {p.as_posix()}: {exc}")
                continue
            if not pattern.search(text):
                failures.append(
                    f"stale tracked file {p.as_posix()} (kind={kind}): does not "
                    f"contain the current version {current} where expected — run "
                    f"`python scripts/bump_version.py --to {current}` or fix it"
                )
    return failures


def _classify_spec_matchers(
    manifest: dict[str, list[dict[str, str]]],
) -> tuple[list[str], list[str]]:
    """Return (tracked_specs, frozen_specs) as deduplicated path/glob lists."""
    tracked = sorted({e["path"] for e in manifest["tracked"]})
    frozen = sorted({e["path"] for e in manifest["frozen"]})
    return tracked, frozen


def check_never_skip(
    bump: Any, manifest: dict[str, list[dict[str, str]]]
) -> list[str]:
    """Hard-fail any git-tracked file with a project-version literal that is
    in NEITHER tracked NOR frozen.

    Returns a list of failure strings (one per unclassified file).
    """
    tracked_specs, frozen_specs = _classify_spec_matchers(manifest)
    all_tracked = bump.tracked_files()

    # Pre-expand every spec into the concrete set of classified files.
    classified: set[str] = set()
    for spec in tracked_specs + frozen_specs:
        for p in bump.expand_manifest_path(spec, all_tracked):
            classified.add(p.as_posix())

    failures: list[str] = []
    for p in all_tracked:
        posix = p.as_posix()
        if posix in classified:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Binary / unreadable files cannot carry a text version literal.
            continue
        if PROJECT_VERSION_RE.search(text):
            failures.append(
                f"untracked version reference in {posix} — classify it in "
                f"scripts/version_tracked_files.yaml (tracked or frozen)"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="emit a machine-readable JSON report"
    )
    args = parser.parse_args(argv)

    bump = _load_bump_module()
    manifest = bump.load_manifest()
    current = bump.detect_current_version()

    coverage_failures = check_coverage(bump, manifest, current)
    never_skip_failures = check_never_skip(bump, manifest)
    all_failures = coverage_failures + never_skip_failures

    if args.json:
        report = {
            "current_version": current,
            "ok": not all_failures,
            "coverage_failures": coverage_failures,
            "never_skip_failures": never_skip_failures,
        }
        print(json.dumps(report, indent=2))
        return 0 if not all_failures else 1

    print(f"check_version_consistency: current project version = {current}")
    print(
        f"  manifest: {len(manifest['tracked'])} tracked entr(ies), "
        f"{len(manifest['frozen'])} frozen entr(ies)"
    )

    if coverage_failures:
        print()
        print(f"COVERAGE FAILURES ({len(coverage_failures)}):")
        for f in coverage_failures:
            print(f"  - {f}")
    else:
        print("  coverage: PASS — every tracked file holds the current version.")

    if never_skip_failures:
        print()
        print(f"NEVER-SKIP FAILURES ({len(never_skip_failures)}):")
        for f in never_skip_failures:
            print(f"  - {f}")
    else:
        print("  never-skip: PASS — no unclassified project-version literal.")

    print()
    if all_failures:
        print(
            f"check_version_consistency: FAIL ({len(all_failures)} issue(s)). "
            "See scripts/version_tracked_files.yaml."
        )
        return 1
    print("check_version_consistency: PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
