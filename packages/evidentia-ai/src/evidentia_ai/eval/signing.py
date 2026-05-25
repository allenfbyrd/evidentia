"""Deprecated shim — moved to ``evidentia_eval.signing`` in v0.10.5 P9.

Re-exports the full public surface of :mod:`evidentia_eval.signing`
so existing ``from evidentia_ai.eval.signing import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.signing is deprecated; use evidentia_eval.signing. "
    "This shim will be removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.signing import (  # noqa: E402
    sign_eval_result,
    verify_eval_result,
)

__all__ = ["sign_eval_result", "verify_eval_result"]
