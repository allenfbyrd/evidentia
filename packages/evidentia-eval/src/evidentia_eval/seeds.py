"""Normalization + hashing utilities for the determinism harness.

These helpers define what "byte-equivalent" means for the
DFAH determinism + replay-equivalence checks. They run BEFORE
the SHA-256 hash + the modal-output comparison so two outputs
that differ only in whitespace or trailing punctuation are
treated as equivalent — auditor-defensible because LLM output
formatting drift on whitespace alone doesn't change the
substantive claim.

The normalization is intentionally minimal:

- Strip leading + trailing whitespace.
- Collapse runs of internal whitespace to a single space.
- Strip trailing terminator punctuation (``.``, ``!``, ``?``)
  + any whitespace following it.
- Preserve everything else verbatim. Internal punctuation,
  case, and non-terminator characters are NOT touched —
  ``"AC-2."`` and ``"AC-2!"`` hash identically (both
  trail-stripped), but ``"Risk."`` and ``"risk."`` do NOT
  (case is preserved).

The harness does NOT do semantic equivalence (no embedding
similarity, no LLM-judged paraphrase detection). That would
make CI gates flaky + would obscure real determinism
regressions. If two outputs differ in any non-whitespace,
non-trailing-terminator way, that's a determinism violation.

v0.8.0 review note (F6): the trailing-terminator collapse
treats ``.``, ``!``, and ``?`` as interchangeable for
determinism purposes. Operators wanting stricter
equivalence (e.g., punctuation-distinct outputs flagged as
violations) should use the raw ``hashlib.sha256`` of the
caller's output without normalization — but expect noise
from harmless whitespace drift.
"""

from __future__ import annotations

import hashlib
import re

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[.!?]+\s*$")


def normalize_for_determinism(text: str) -> str:
    """Apply the canonical normalization for determinism comparison.

    Args:
        text: Raw output from the LLM call.

    Returns:
        Normalized form: whitespace-collapsed + trailing-
        punctuation-stripped + lowercased trailing terminator.
        Preserves all other content verbatim.
    """
    # 1. Strip whitespace + collapse internal runs.
    out = _WHITESPACE_RE.sub(" ", text.strip())
    # 2. Strip trailing punctuation/whitespace (don't penalize a
    # generator that adds a period the next call doesn't).
    out = _TRAILING_PUNCT_RE.sub("", out)
    return out


def hash_output(text: str) -> str:
    """SHA-256 hex digest of the normalized output.

    Used by:
    - Replay equivalence check (re-run hash == original hash).
    - Determinism modal-output histogram (group equivalent
      outputs by hash).

    Args:
        text: Raw output from the LLM call. Will be normalized
            via :func:`normalize_for_determinism` before hashing.

    Returns:
        SHA-256 hex digest (64 lowercase hex chars).
    """
    normalized = normalize_for_determinism(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
