"""Deprecated shim — moved to ``evidentia_eval.faithfulness_semantic`` in v0.10.5 P9.

Re-exports the full public surface of
:mod:`evidentia_eval.faithfulness_semantic` so existing
``from evidentia_ai.eval.faithfulness_semantic import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.

The optional sentence-transformers stack lives on the
``evidentia-eval[faithfulness-semantic]`` extra now (renamed from
the v0.8.3 ``evidentia-ai[eval-faithfulness]``).
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.faithfulness_semantic is deprecated; use "
    "evidentia_eval.faithfulness_semantic. This shim will be "
    "removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.faithfulness_semantic import (  # noqa: E402
    DEFAULT_SEMANTIC_MODEL,
    DEFAULT_SEMANTIC_THRESHOLD,
    SemanticFaithfulnessNotAvailableError,
    faithfulness_score_semantic,
)

__all__ = [
    "DEFAULT_SEMANTIC_MODEL",
    "DEFAULT_SEMANTIC_THRESHOLD",
    "SemanticFaithfulnessNotAvailableError",
    "faithfulness_score_semantic",
]
