"""[DEPRECATED 2026-04-25] Historical reference: bulk content-rename script.

Used exactly once during the v0.6.0 ControlBridge -> Evidentia rename
release (April 2026). Retained in the repo for transparency about
how the rename was performed; not safe to re-run because the source
patterns no longer exist anywhere except in CHANGELOG entries,
RENAMED.md, and historical migration shims (which were themselves
removed at v0.7.0 per the public contract).

Do not invoke this script. The rename is complete.

----- Original docstring (v0.6.0) -----

One-shot bulk content rename: controlbridge → evidentia across tracked files.

Runs three case-sensitive replacements in a single pass per file:
  - lowercase: controlbridge  → evidentia
  - title   : ControlBridge   → Evidentia
  - upper   : CONTROLBRIDGE   → EVIDENTIA

Scope:
  - Only `git ls-files` tracked files (skips .venv, dist/, node_modules, caches).
  - Skips binary/lockfile/generated files by extension AND by explicit skiplist.
  - Skips this script itself (self-reference would create false positives).

After running, `uv.lock` and `packages/evidentia-ui/package-lock.json` must be
regenerated via `uv sync` / `npm install` — those are NOT edited in place.

Usage: python scripts/_rename_content.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# --- configuration --------------------------------------------------------

REPLACEMENTS: list[tuple[str, str]] = [
    ("controlbridge", "evidentia"),
    ("ControlBridge", "Evidentia"),
    ("CONTROLBRIDGE", "EVIDENTIA"),
]

# File extensions we touch. Everything else is skipped even if tracked.
TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".toml",
        ".md",
        ".yml",
        ".yaml",
        ".tsx",
        ".ts",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".json",
        ".html",
        ".css",
        ".txt",
        ".cfg",
        ".ini",
        ".sh",
        ".ps1",
        ".bat",
        ".typed",
    }
)

# Files we explicitly refuse to rewrite (regenerate via tooling instead).
SKIP_PATHS: frozenset[str] = frozenset(
    {
        "uv.lock",
        "packages/evidentia-ui/package-lock.json",
        "scripts/_rename_content.py",
    }
)

# --- driver ---------------------------------------------------------------


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [Path(p) for p in result.stdout.splitlines() if p]


def replace_in(text: str) -> tuple[str, int]:
    count = 0
    for old, new in REPLACEMENTS:
        count += text.count(old)
        text = text.replace(old, new)
    return text, count


def main() -> int:
    files = tracked_files()
    files_scanned = 0
    files_changed = 0
    total_replacements = 0

    for p in files:
        posix_path = p.as_posix()
        if posix_path in SKIP_PATHS:
            continue
        # Filter by extension
        if p.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            original = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, PermissionError):
            continue

        files_scanned += 1
        new_text, count = replace_in(original)
        if count > 0 and new_text != original:
            p.write_text(new_text, encoding="utf-8")
            files_changed += 1
            total_replacements += count

    print(f"scanned={files_scanned} files_changed={files_changed} total_replacements={total_replacements}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
