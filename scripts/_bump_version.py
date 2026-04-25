"""[DEPRECATED 2026-04-25] Historical reference: v0.5.0 -> v0.6.0 version bumper.

Used exactly once during the v0.6.0 rename release (April 2026) to
bump version strings + inter-package dep pins from the 0.5.x series
to the 0.6.x series. Retained in the repo for transparency about how
the bump was performed; not safe to re-run because the source
patterns (>=0.5.0,<0.6.0) no longer exist in any current pyproject.toml.

For future version bumps, perform the equivalent set of edits manually
or write a fresh script targeting the actual current/target versions.
The Step-3 review of v0.7.0 caught a real bug (commit 25ccca8) that
would have been prevented by a generalized version-bumper that handles
inter-package pins atomically — consider this for v0.7.1+ tooling.

----- Original docstring (v0.6.0) -----

One-shot version bump: 0.5.0 -> 0.6.0 for the v0.6.0 rename release.

Bumps three patterns across tracked config files:
  - `version = "0.5.0"`           (pyproject.toml)
  - `"version": "0.5.0"`          (package.json)
  - `>=0.5.0,<0.6.0`              (inter-package pins; widened to 0.6.0 series)

After running, re-run `uv sync --all-packages` to regenerate `uv.lock`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPLACEMENTS: list[tuple[str, str]] = [
    ('version = "0.5.0"', 'version = "0.6.0"'),
    ('"version": "0.5.0"', '"version": "0.6.0"'),
    (">=0.5.0,<0.6.0", ">=0.6.0,<0.7.0"),
]

TARGET_EXTENSIONS: frozenset[str] = frozenset({".toml", ".json"})


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [Path(p) for p in result.stdout.splitlines() if p]


def main() -> int:
    files_changed = 0
    total = 0
    for p in tracked_files():
        if p.suffix.lower() not in TARGET_EXTENSIONS:
            continue
        # Skip lockfiles.
        if p.name in {"uv.lock", "package-lock.json"}:
            continue
        try:
            original = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, PermissionError):
            continue
        new_text = original
        count = 0
        for old, new in REPLACEMENTS:
            count += new_text.count(old)
            new_text = new_text.replace(old, new)
        if new_text != original:
            p.write_text(new_text, encoding="utf-8")
            files_changed += 1
            total += count
            print(f"  {p}: {count} replacement(s)")
    print(f"files_changed={files_changed} total_replacements={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
