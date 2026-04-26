#!/usr/bin/env python3
"""Atomically bump version + inter-package pin ranges across the Evidentia monorepo.

Replaces the deprecated scripts/_bump_version.py (which was hardcoded
0.5 -> 0.6). This one is general: pass --from X.Y.Z --to A.B.C (or just
--to A.B.C and it auto-detects current).

Updates three patterns across tracked .toml + .json files:
  - version = "X.Y.Z"            (pyproject.toml)
  - "version": "X.Y.Z"           (package.json)
  - >=X.Y.Z,<X.(Y+1).0           (inter-package pins; widens to next minor)

Skips lockfiles (uv.lock, package-lock.json) - those are regenerated
by `uv sync --all-packages` after running this script.

Usage:
  ./scripts/bump_version.py --to 0.8.0
  ./scripts/bump_version.py --from 0.7.0 --to 0.7.1
  ./scripts/bump_version.py --to 0.7.1 --dry-run  # show what would change

Per the publishing-authority protocol (~/.claude/CLAUDE.md), this script
NEVER pushes, tags, or publishes. It only edits files. Use git status
afterward + commit explicitly. Tag creation requires explicit user
approval per the global protocol.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def tracked_files() -> list[Path]:
    """All git-tracked files (so we never touch generated/ignored content)."""
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def detect_current_version() -> str:
    """Read evidentia-core's pyproject.toml as the source of truth."""
    p = Path("packages/evidentia-core/pyproject.toml")
    if not p.exists():
        sys.exit(
            "Cannot detect current version: "
            "packages/evidentia-core/pyproject.toml missing"
        )
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*version\s*=\s*"(\d+\.\d+\.\d+)"', line)
        if m:
            return m.group(1)
    sys.exit("Cannot find version field in evidentia-core/pyproject.toml")


def bump_pin_range(current: str, target: str) -> tuple[str, str]:
    """Return (current-range, next-range) for inter-package pin updates.

    Pin convention is `>={M}.{m}.0,<{M}.{m+1}.0` (next minor as upper bound).
    """
    cur_maj, cur_min, _ = current.split(".")
    tgt_maj, tgt_min, _ = target.split(".")
    cur_range = f">={cur_maj}.{cur_min}.0,<{cur_maj}.{int(cur_min)+1}.0"
    tgt_range = f">={tgt_maj}.{tgt_min}.0,<{tgt_maj}.{int(tgt_min)+1}.0"
    return cur_range, tgt_range


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--from",
        dest="frm",
        help="current version (auto-detected from evidentia-core if omitted)",
    )
    ap.add_argument("--to", required=True, help="target version, e.g. 0.7.1")
    ap.add_argument(
        "--dry-run", action="store_true", help="print changes without writing"
    )
    args = ap.parse_args()

    if not VERSION_RE.fullmatch(args.to):
        sys.exit(f"--to must be X.Y.Z, got {args.to!r}")
    current = args.frm or detect_current_version()
    if not VERSION_RE.fullmatch(current):
        sys.exit(f"--from must be X.Y.Z, got {current!r}")
    if current == args.to:
        print(f"Already at {args.to} - nothing to do.")
        return 0

    cur_pin, tgt_pin = bump_pin_range(current, args.to)
    replacements = [
        (f'version = "{current}"', f'version = "{args.to}"'),
        (f'"version": "{current}"', f'"version": "{args.to}"'),
        (cur_pin, tgt_pin),
    ]

    print(f"Bump plan: {current} -> {args.to}")
    print(f"  Inter-package pins: {cur_pin} -> {tgt_pin}")
    print()

    files_changed = 0
    total_subs = 0
    for p in tracked_files():
        if p.suffix.lower() not in {".toml", ".json"}:
            continue
        if p.name in {"uv.lock", "package-lock.json"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        new_text = text
        file_subs = 0
        for old, new in replacements:
            n = new_text.count(old)
            if n:
                new_text = new_text.replace(old, new)
                file_subs += n
        if file_subs:
            print(f"  {p}: {file_subs} substitution(s)")
            if not args.dry_run:
                p.write_text(new_text, encoding="utf-8")
            files_changed += 1
            total_subs += file_subs

    print()
    suffix = " [DRY RUN]" if args.dry_run else ""
    print(
        f"Summary: {files_changed} file(s), {total_subs} substitution(s){suffix}"
    )
    if not args.dry_run and files_changed > 0:
        print()
        print("Next steps (per the publishing-authority protocol, do these manually):")
        print(f"  1. uv sync --all-packages   # regenerate uv.lock at {args.to}")
        print("  2. Run pytest + mypy + ruff to confirm nothing broke")
        print(
            f"  3. git add -p && git commit -m 'chore(release): bump to {args.to}'"
        )
        print(f"  4. (When ready, with explicit approval) push to main + tag v{args.to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
