"""Deprecated shim — ``evidentia_ai.eval`` moved to ``evidentia_eval`` in v0.10.5 P9.

The DFAH determinism + faithfulness harness was extracted from
``evidentia-ai`` to a dedicated ``evidentia-eval`` workspace
package so air-gap installs of the production risk-statement
runtime no longer pull the dev-time eval stack.

Existing code using ``from evidentia_ai.eval import …`` continues
to work via this shim, which re-exports everything from
``evidentia_eval``. A :class:`DeprecationWarning` fires at import
time so test suites + CI logs flag the call site.

**Removal timeline**: scheduled for **v0.12.0**. Migrate to:

.. code-block:: python

    from evidentia_eval import DFAHarness, EvalSample  # new

instead of:

.. code-block:: python

    from evidentia_ai.eval import DFAHarness, EvalSample  # deprecated
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval is deprecated; use evidentia_eval directly. "
    "This shim will be removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the full public surface. The list mirrors
# evidentia_eval.__all__ so a wildcard import from the shim is
# equivalent to a wildcard import from the new location.
from evidentia_eval import (  # noqa: E402
    CLAIM_EXTRACTION_PROMPT,
    DEFAULT_FAITHFULNESS_THRESHOLD,
    DEFAULT_SEMANTIC_MODEL,
    DEFAULT_SEMANTIC_THRESHOLD,
    DeterminismResult,
    DFAHarness,
    EvalResult,
    EvalSample,
    FaithfulnessResult,
    PromptFaithfulnessResult,
    ReplayResult,
    SemanticFaithfulnessNotAvailableError,
    determinism_score,
    extract_claims,
    faithfulness_score,
    faithfulness_score_semantic,
    hash_output,
    normalize_for_determinism,
    replay_equivalent,
    sign_eval_result,
    verify_eval_result,
)

__all__ = [
    "CLAIM_EXTRACTION_PROMPT",
    "DEFAULT_FAITHFULNESS_THRESHOLD",
    "DEFAULT_SEMANTIC_MODEL",
    "DEFAULT_SEMANTIC_THRESHOLD",
    "DFAHarness",
    "DeterminismResult",
    "EvalResult",
    "EvalSample",
    "FaithfulnessResult",
    "PromptFaithfulnessResult",
    "ReplayResult",
    "SemanticFaithfulnessNotAvailableError",
    "determinism_score",
    "extract_claims",
    "faithfulness_score",
    "faithfulness_score_semantic",
    "hash_output",
    "normalize_for_determinism",
    "replay_equivalent",
    "sign_eval_result",
    "verify_eval_result",
]
