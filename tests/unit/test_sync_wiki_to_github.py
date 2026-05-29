"""Tests for the GitHub-wiki flattener (scripts/sync_wiki_to_github.py).

The wiki sync maps the in-repo `docs/wiki/` tree (which has nested
sections + a 3-level `4-reference/api/` subdirectory) onto GitHub's
FLAT wiki namespace. A path-depth the flattener doesn't handle raises
ValueError and fails the sync workflow (regression: the 7 per-package
API pages at `4-reference/api/*.md` once tripped this). These tests
pin the mapping + guarantee every real wiki page flattens without error.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync_wiki_to_github.py"
_spec = importlib.util.spec_from_file_location("sync_wiki_to_github", _SCRIPT)
assert _spec and _spec.loader
sync_wiki = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_wiki)

WIKI_SRC = sync_wiki.WIKI_SRC


def _name(rel: str) -> str:
    return sync_wiki.wiki_flat_name(WIKI_SRC / rel)


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("index.md", "Home"),
        ("1-getting-started/index.md", "Getting-Started"),
        ("1-getting-started/quickstart.md", "Quickstart"),
        ("5-compliance/osps-baseline-mapping.md", "OSPS-Baseline-Mapping"),
        ("6-project/api-stability.md", "API-Stability"),
        # 3-level api/ pages (the regression target):
        ("4-reference/api/evidentia-core.md", "API-Evidentia-Core"),
        ("4-reference/api/evidentia-mcp.md", "API-Evidentia-MCP"),
        ("4-reference/api/evidentia-ai.md", "API-Evidentia-AI"),
    ],
)
def test_wiki_flat_name_mapping(rel: str, expected: str) -> None:
    assert _name(rel) == expected


def test_api_pages_do_not_raise() -> None:
    """The 3-level api/ paths must flatten, not raise ValueError."""
    for pkg in ("core", "ai", "api", "collectors", "eval", "integrations", "mcp"):
        name = _name(f"4-reference/api/evidentia-{pkg}.md")
        assert name.startswith("API-Evidentia-")


def test_every_real_wiki_page_flattens_without_error() -> None:
    """build_link_map() over the live docs/wiki/ tree must not raise +
    must yield unique flat names (no two pages collide on the wiki)."""
    link_map = sync_wiki.build_link_map()
    assert link_map, "expected at least one wiki page"
    names = list(link_map.values())
    assert len(names) == len(set(names)), "wiki flat-name collision detected"


def test_unexpected_depth_still_raises() -> None:
    """A 4-level path remains an explicit error (don't silently mishandle)."""
    with pytest.raises(ValueError, match="Unexpected wiki path depth"):
        sync_wiki.wiki_flat_name(WIKI_SRC / "a/b/c/d.md")
