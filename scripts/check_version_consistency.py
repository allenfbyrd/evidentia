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

  3. ANCHORS — for each ``anchors`` overlay entry, assert that every anchored
     line (a line in ``path`` containing the literal ``line_contains``
     substring) carries EXACTLY ONE in-family project-version literal and that
     the single literal EQUALS the CURRENT version. This re-arms a LIVE
     "current version" line that lives inside a file which is ``frozen``
     WHOLESALE (the frozen membership exempts the whole file from never-skip,
     so a drifted live line would otherwise go uncaught). Anchors are ALWAYS
     coverage-required, with misconfiguration guards (malformed entry, path
     matches no file, marker matches 0 lines, anchored line has 0 OR >1 version
     literals, anchor file unclassified). The >1 guard closes the multi-literal
     footgun where a second in-family token on the line (a historical project
     version or a third-party >=0.7 dependency version) would let the gate pass
     a stale live token while the bumper silently corrupts the second literal.

The "current version" source of truth is
``packages/evidentia-core/pyproject.toml``'s ``version`` field — the same
detector the bumper uses.

The per-``kind`` COVERAGE patterns are obtained from
``bump_version.replacements_for_kind`` (the regex half of each
(regex, replacement) pair matches the version it is searching for), so the
gate and the bumper can never use divergent patterns.

Exit codes:
    0 — PASS (coverage holds + no unclassified literal + anchors current)
    1 — FAIL (a tracked file is stale, an unclassified literal exists, OR an
        anchored line is stale / misconfigured)
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


def check_never_skip(
    bump: Any, manifest: dict[str, list[dict[str, str]]]
) -> list[str]:
    """Hard-fail any git-tracked file with a project-version literal that is
    in NEITHER tracked NOR frozen.

    Returns a list of failure strings (one per unclassified file).

    M-2 (DRY): the tracked∪frozen union is built by the shared
    ``bump.classified_paths`` helper (the SAME one the anchor overlay uses), so
    there is exactly ONE definition of "the classified set" across both tools —
    the bumper's ``apply_anchors`` and this gate can never compute it
    differently.
    """
    all_tracked = bump.tracked_files()
    classified = bump.classified_paths(manifest, all_tracked)

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


def check_anchors(
    bump: Any, manifest: dict[str, list[dict[str, str]]], current: str
) -> list[str]:
    """Assert every anchored line holds EXACTLY ONE current-version literal.

    For each ``anchors`` entry, every line in ``path`` containing the literal
    ``line_contains`` substring is an "anchored line". The EXACTLY-ONE-live-
    literal contract requires that line to carry EXACTLY ONE in-family
    project-version literal (matched by ``bump.ANCHOR_VERSION_RE``) and that the
    single literal EQUAL ``current`` (optionally ``v``-prefixed). A stale
    anchored line is a HARD FAIL — this is the safeguard the file's wholesale
    ``frozen`` membership defeats.

    Returns a list of human-readable failure strings (empty == pass). Covers the
    misconfiguration cases as failures too:
      * an anchor entry missing/mistyping ``path`` / ``line_contains`` (a clean
        appended failure, not a raw KeyError);
      * ``path`` matches no git-tracked file;
      * the anchor's file is in NEITHER ``tracked`` NOR ``frozen``;
      * ``line_contains`` matches 0 lines;
      * an anchored line carries NO project-version literal;
      * an anchored line carries MORE THAN ONE project-version literal
        (ambiguous anchor — closes the multi-literal footgun where a second
        in-family token on the line would let the gate pass a stale live token
        while the bumper silently corrupts the second literal).
    """
    anchors = manifest.get("anchors") or []
    if not anchors:
        return []
    failures: list[str] = []
    all_tracked = bump.tracked_files()
    classified = bump.classified_paths(manifest, all_tracked)

    for entry in anchors:
        # M-1: validate entry shape up front; a malformed entry becomes a clean
        # appended failure (the checker accumulates strings; it never exits).
        try:
            spec = bump._require_anchor_str(entry, "path")
            marker = bump._require_anchor_str(entry, "line_contains")
        except SystemExit as exc:
            failures.append(str(exc))
            continue
        matched_files = bump.expand_manifest_path(spec, all_tracked)
        if not matched_files:
            failures.append(
                f"anchor path '{spec}' matched no git-tracked file — fix the "
                f"path in scripts/version_tracked_files.yaml"
            )
            continue
        for p in matched_files:
            posix = p.as_posix()
            if posix not in classified:
                failures.append(
                    f"anchor file {posix} is in NEITHER tracked NOR frozen — an "
                    f"anchor is a coverage overlay, not a substitute for "
                    f"never-skip classification; also classify it in "
                    f"scripts/version_tracked_files.yaml"
                )
                continue
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                failures.append(f"cannot read anchor file {posix}: {exc}")
                continue
            marked = [ln for ln in lines if marker in ln]
            if not marked:
                failures.append(
                    f"anchor marker '{marker}' matched 0 lines in {posix} — fix "
                    f"the line_contains substring in "
                    f"scripts/version_tracked_files.yaml"
                )
                continue
            for ln in marked:
                found_all = bump.ANCHOR_VERSION_RE.findall(ln)
                if len(found_all) == 0:
                    failures.append(
                        f"anchor line in {posix} containing '{marker}' carries "
                        f"no project-version literal — fix the anchor in "
                        f"scripts/version_tracked_files.yaml"
                    )
                    continue
                if len(found_all) > 1:
                    failures.append(
                        f"ambiguous anchor: line containing '{marker}' in "
                        f"{posix} has {len(found_all)} project-version literals; "
                        f"use a more specific line_contains so exactly ONE live "
                        f"version is anchored"
                    )
                    continue
                # Exactly one literal — it MUST equal current (not merely be
                # present somewhere on the line). Strip an optional leading ``v``
                # from the matched token and compare its numeric body.
                m = bump.ANCHOR_VERSION_RE.search(ln)
                found = m.group(0) if m else "?"
                numeric = found[1:] if found.startswith("v") else found
                if numeric != current:
                    failures.append(
                        f"anchor stale in {posix}: line containing '{marker}' "
                        f"shows {found} not {current}; run "
                        f"scripts/bump_version.py"
                    )
    return failures


def check_decisions_documented(
    manifest: dict[str, list[dict[str, str]]],
) -> list[str]:
    """Every ``tracked`` / ``frozen`` / ``anchor`` entry MUST carry a non-empty
    ``desc``.

    The ``desc`` is the per-entry decision rationale — the "why" recorded
    alongside the machine-readable classification (see
    ``docs/version-decisions.md``). Requiring it means a classification can never
    be added to the manifest without being documented, so the bumper follows a
    recorded decision and never silently re-litigates one.
    """
    failures: list[str] = []
    for section in ("tracked", "frozen", "anchors"):
        for entry in manifest.get(section) or []:
            path = entry.get("path", "<no-path>")
            desc = entry.get("desc")
            if not isinstance(desc, str) or not desc.strip():
                failures.append(
                    f"undocumented {section} entry {path!r} — add a non-empty "
                    f"'desc' rationale in scripts/version_tracked_files.yaml "
                    f"(see docs/version-decisions.md)"
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
    anchor_failures = check_anchors(bump, manifest, current)
    decisions_failures = check_decisions_documented(manifest)
    all_failures = (
        coverage_failures
        + never_skip_failures
        + anchor_failures
        + decisions_failures
    )

    if args.json:
        report = {
            "current_version": current,
            "ok": not all_failures,
            "coverage_failures": coverage_failures,
            "never_skip_failures": never_skip_failures,
            "anchor_failures": anchor_failures,
            "decisions_failures": decisions_failures,
        }
        print(json.dumps(report, indent=2))
        return 0 if not all_failures else 1

    print(f"check_version_consistency: current project version = {current}")
    print(
        f"  manifest: {len(manifest['tracked'])} tracked entr(ies), "
        f"{len(manifest['frozen'])} frozen entr(ies), "
        f"{len(manifest.get('anchors') or [])} anchor entr(ies)"
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

    if anchor_failures:
        print()
        print(f"ANCHOR FAILURES ({len(anchor_failures)}):")
        for f in anchor_failures:
            print(f"  - {f}")
    else:
        print("  anchors: PASS — every anchored live-version line is current.")

    if decisions_failures:
        print()
        print(f"UNDOCUMENTED-DECISION FAILURES ({len(decisions_failures)}):")
        for f in decisions_failures:
            print(f"  - {f}")
    else:
        print("  decisions: PASS — every manifest entry carries a rationale.")

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
