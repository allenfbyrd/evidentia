"""Deprecated shim — moved to ``evidentia_eval.seeds`` in v0.10.5 P9.

Re-exports the full public surface of :mod:`evidentia_eval.seeds`
so existing ``from evidentia_ai.eval.seeds import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.seeds is deprecated; use evidentia_eval.seeds. "
    "This shim will be removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.seeds import (  # noqa: E402
    hash_output,
    normalize_for_determinism,
)

__all__ = ["hash_output", "normalize_for_determinism"]
