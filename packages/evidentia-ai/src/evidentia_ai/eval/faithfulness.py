"""Deprecated shim — moved to ``evidentia_eval.faithfulness`` in v0.10.5 P9.

Re-exports the full public surface of :mod:`evidentia_eval.faithfulness`
so existing ``from evidentia_ai.eval.faithfulness import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.faithfulness is deprecated; use evidentia_eval.faithfulness. "
    "This shim will be removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.faithfulness import (  # noqa: E402
    DEFAULT_FAITHFULNESS_THRESHOLD,
    FaithfulnessResult,
    PromptFaithfulnessResult,
    faithfulness_score,
    resolve_threshold,
)

__all__ = [
    "DEFAULT_FAITHFULNESS_THRESHOLD",
    "FaithfulnessResult",
    "PromptFaithfulnessResult",
    "faithfulness_score",
    "resolve_threshold",
]
