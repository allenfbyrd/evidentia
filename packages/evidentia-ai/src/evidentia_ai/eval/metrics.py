"""Deprecated shim — moved to ``evidentia_eval.metrics`` in v0.10.5 P9.

Re-exports the full public surface of :mod:`evidentia_eval.metrics`
so existing ``from evidentia_ai.eval.metrics import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.metrics is deprecated; use evidentia_eval.metrics. "
    "This shim will be removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.metrics import (  # noqa: E402
    DeterminismResult,
    ReplayResult,
    determinism_score,
    replay_equivalent,
)

__all__ = [
    "DeterminismResult",
    "ReplayResult",
    "determinism_score",
    "replay_equivalent",
]
