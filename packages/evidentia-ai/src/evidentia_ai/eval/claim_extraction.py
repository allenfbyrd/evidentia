"""Deprecated shim — moved to ``evidentia_eval.claim_extraction`` in v0.10.5 P9.

Re-exports the full public surface of
:mod:`evidentia_eval.claim_extraction` so existing
``from evidentia_ai.eval.claim_extraction import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.claim_extraction is deprecated; use "
    "evidentia_eval.claim_extraction. This shim will be removed "
    "in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.claim_extraction import (  # noqa: E402
    CLAIM_EXTRACTION_PROMPT,
    extract_claims,
)

__all__ = ["CLAIM_EXTRACTION_PROMPT", "extract_claims"]
