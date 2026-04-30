"""Tests for ``evidentia_core.security.paths.validate_within``."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from evidentia_core.security.paths import (
    PathTraversalError,
    validate_within,
)


def test_returns_resolved_path_for_descendant(tmp_path: Path) -> None:
    safe_root = tmp_path
    candidate = safe_root / "report.json"
    candidate.write_text("{}", encoding="utf-8")

    resolved = validate_within(candidate, safe_root)

    assert resolved == candidate.resolve()
    assert resolved.is_file()


def test_returns_resolved_path_for_nested_descendant(tmp_path: Path) -> None:
    safe_root = tmp_path
    nested = safe_root / "a" / "b" / "c.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")

    resolved = validate_within(nested, safe_root)

    assert resolved == nested.resolve()


def test_returns_resolved_path_for_root_itself(tmp_path: Path) -> None:
    resolved = validate_within(tmp_path, tmp_path)

    assert resolved == tmp_path.resolve()


def test_accepts_nonexistent_descendant(tmp_path: Path) -> None:
    """New-file write destinations must validate even before they exist."""
    candidate = tmp_path / "new" / "subdir" / "report.json"
    # parent does not exist; file does not exist
    resolved = validate_within(candidate, tmp_path)
    assert resolved == candidate.resolve()


def test_rejects_dotdot_traversal(tmp_path: Path) -> None:
    safe_root = tmp_path / "store"
    safe_root.mkdir()
    sibling = tmp_path / "outside.json"
    sibling.write_text("secret", encoding="utf-8")
    candidate = safe_root / ".." / "outside.json"

    with pytest.raises(PathTraversalError):
        validate_within(candidate, safe_root)


def test_rejects_absolute_path_outside_root(tmp_path: Path) -> None:
    safe_root = tmp_path / "store"
    safe_root.mkdir()
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("x", encoding="utf-8")

    with pytest.raises(PathTraversalError):
        validate_within(elsewhere, safe_root)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlink creation requires elevated privileges on Windows",
)
def test_rejects_symlink_escape(tmp_path: Path) -> None:
    """A symlink inside the safe root that points outside is rejected."""
    safe_root = tmp_path / "store"
    safe_root.mkdir()
    target = tmp_path / "outside.json"
    target.write_text("secret", encoding="utf-8")
    link = safe_root / "trojan.json"
    os.symlink(target, link)

    with pytest.raises(PathTraversalError):
        validate_within(link, safe_root)


def test_path_traversal_error_is_value_error_subclass() -> None:
    """Existing ``except ValueError`` handlers must catch traversal errors."""
    assert issubclass(PathTraversalError, ValueError)


def test_error_message_does_not_echo_candidate(tmp_path: Path) -> None:
    """Avoid reflecting the offending input in the error message."""
    safe_root = tmp_path / "store"
    safe_root.mkdir()
    candidate = safe_root / ".." / "secret-attack-string.json"

    with pytest.raises(PathTraversalError) as excinfo:
        validate_within(candidate, safe_root)

    assert "secret-attack-string" not in str(excinfo.value)
