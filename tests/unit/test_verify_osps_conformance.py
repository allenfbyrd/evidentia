"""Tests for ``scripts/verify_osps_conformance.py`` (D2.3, v0.10.7).

This module was extracted from the embedded ``python <<'PY'`` heredoc in
``.github/workflows/verify-osps-conformance.yml`` so the URL-translation
logic is unit-testable. These tests pin the ``translate_url`` contract
for every URL shape it handles + the table-row claim parser. They do NOT
invoke ``gh`` / the network (the 404-probe path is environment-dependent
and out of scope for unit tests).

``translate_url`` shapes covered (each asserts BOTH the api_endpoint and
the shape label of the returned tuple):

1. ``blob``               — /blob/main/<path>  -> contents API
2. ``tree``               — /tree/main/<dir>   -> contents API (rstrip /)
3. ``release-tag``        — /releases/tag/<t>  -> releases/tags API
4. ``commits-ref``        — /commits/<ref>     -> branches API
5. ``security-advisories``— /security/advisories -> security-advisories
6. ``repo-root``          — repo root          -> repos/<owner>/<repo>
7. ``unmapped``           — anything else (hard-fail signal)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_osps_conformance.py"


@pytest.fixture(scope="module")
def voc() -> Any:
    """Import scripts/verify_osps_conformance.py (it has no __init__.py)."""
    spec = importlib.util.spec_from_file_location("verify_osps_conformance", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_osps_conformance"] = module
    spec.loader.exec_module(module)
    return module


# The owner/repo the script pins for URL translation.
OWNER_REPO = "Polycentric-Labs/evidentia"
BASE = f"https://github.com/{OWNER_REPO}"


def test_translate_blob_simple(voc: Any) -> None:
    endpoint, shape = voc.translate_url(f"{BASE}/blob/main/SECURITY.md")
    assert shape == "blob"
    assert endpoint == f"repos/{OWNER_REPO}/contents/SECURITY.md?ref=main"


def test_translate_blob_nested_path(voc: Any) -> None:
    # A deep path (e.g. a workflow file) must be preserved verbatim.
    endpoint, shape = voc.translate_url(f"{BASE}/blob/main/.github/workflows/release.yml")
    assert shape == "blob"
    assert endpoint == f"repos/{OWNER_REPO}/contents/.github/workflows/release.yml?ref=main"


def test_translate_tree_dir(voc: Any) -> None:
    endpoint, shape = voc.translate_url(f"{BASE}/tree/main/docs")
    assert shape == "tree"
    assert endpoint == f"repos/{OWNER_REPO}/contents/docs?ref=main"


def test_translate_tree_strips_trailing_slash(voc: Any) -> None:
    # A trailing slash on a tree URL must be stripped before building the
    # contents endpoint (otherwise the API path would have a stray slash).
    endpoint, shape = voc.translate_url(f"{BASE}/tree/main/docs/")
    assert shape == "tree"
    assert endpoint == f"repos/{OWNER_REPO}/contents/docs?ref=main"


def test_translate_release_tag(voc: Any) -> None:
    endpoint, shape = voc.translate_url(f"{BASE}/releases/tag/v0.10.5")
    assert shape == "release-tag"
    assert endpoint == f"repos/{OWNER_REPO}/releases/tags/v0.10.5"


def test_translate_commits_ref_maps_to_branches(voc: Any) -> None:
    # /commits/<ref> deliberately maps to the BRANCHES API (returns a
    # clean 404 on a missing branch), not the contents API.
    endpoint, shape = voc.translate_url(f"{BASE}/commits/main")
    assert shape == "commits-ref"
    assert endpoint == f"repos/{OWNER_REPO}/branches/main"


def test_translate_security_advisories(voc: Any) -> None:
    endpoint, shape = voc.translate_url(f"{BASE}/security/advisories")
    assert shape == "security-advisories"
    assert endpoint == f"repos/{OWNER_REPO}/security-advisories"


def test_translate_security_advisories_trailing_slash(voc: Any) -> None:
    endpoint, shape = voc.translate_url(f"{BASE}/security/advisories/")
    assert shape == "security-advisories"
    assert endpoint == f"repos/{OWNER_REPO}/security-advisories"


def test_translate_repo_root(voc: Any) -> None:
    endpoint, shape = voc.translate_url(BASE)
    assert shape == "repo-root"
    assert endpoint == f"repos/{OWNER_REPO}"


def test_translate_repo_root_trailing_slash(voc: Any) -> None:
    endpoint, shape = voc.translate_url(f"{BASE}/")
    assert shape == "repo-root"
    assert endpoint == f"repos/{OWNER_REPO}"


def test_translate_http_scheme_also_matches(voc: Any) -> None:
    # The shape regexes accept http:// as well as https:// (the original
    # embedded patterns used `https?://`).
    endpoint, shape = voc.translate_url(f"http://github.com/{OWNER_REPO}/blob/main/README.md")
    assert shape == "blob"
    assert endpoint == f"repos/{OWNER_REPO}/contents/README.md?ref=main"


def test_translate_unmapped_returns_url_and_label(voc: Any) -> None:
    # An unknown shape is a HARD-FAIL signal: the URL is returned
    # unchanged with the "unmapped" label (the caller exits non-zero).
    url = "https://example.com/not/a/github/url"
    endpoint, shape = voc.translate_url(url)
    assert shape == "unmapped"
    assert endpoint == url


def test_translate_other_repo_is_unmapped(voc: Any) -> None:
    # A github.com URL for a DIFFERENT repo doesn't match the pinned
    # OWNER_REPO patterns and is therefore unmapped (hard-fail), not
    # silently accepted.
    url = "https://github.com/some-other/repo/blob/main/README.md"
    _endpoint, shape = voc.translate_url(url)
    assert shape == "unmapped"


def test_parse_claims_matches_pass_rows_only(voc: Any) -> None:
    md = (
        "# heading\n"
        "\n"
        "| Control | Title | Verdict | Evidence |\n"
        "|---|---|---|---|\n"
        "| OSPS-AC-01.01 | Use MFA | ✅ PASS | "
        "[GOVERNANCE.md](https://github.com/Polycentric-Labs/evidentia/blob/main/GOVERNANCE.md) |\n"
        "| OSPS-AC-04.01 | Least privilege | ⚠ HONEST_GAP | (see below) |\n"
        "| OSPS-BR-02.01 | Versioning | ✅ PASS | "
        "[v0.10.5](https://github.com/Polycentric-Labs/evidentia/releases/tag/v0.10.5) |\n"
    )
    claims = voc.parse_claims(md)
    # Only the two PASS rows; the HONEST_GAP row is excluded.
    ids = [c[0] for c in claims]
    assert ids == ["OSPS-AC-01.01", "OSPS-BR-02.01"]
    # The evidence cell text is captured (used downstream for URL extraction).
    assert "GOVERNANCE.md" in claims[0][1]


def test_url_pattern_extracts_markdown_link(voc: Any) -> None:
    cell = " [SECURITY.md](https://github.com/Polycentric-Labs/evidentia/blob/main/SECURITY.md) "
    urls = voc.URL_PATTERN.findall(cell)
    assert urls == ["https://github.com/Polycentric-Labs/evidentia/blob/main/SECURITY.md"]


def test_main_returns_2_when_doc_missing(voc: Any, tmp_path: Path) -> None:
    # Passing a non-existent path returns exit code 2 (file-not-found).
    missing = tmp_path / "nope.md"
    assert voc.main([str(missing)]) == 2
