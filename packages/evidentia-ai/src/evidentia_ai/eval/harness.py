"""Deprecated shim — moved to ``evidentia_eval.harness`` in v0.10.5 P9.

Re-exports the full public surface of :mod:`evidentia_eval.harness`
so existing ``from evidentia_ai.eval.harness import …`` imports
continue to work. Removal scheduled for v0.12.0; see
:mod:`evidentia_ai.eval` for the migration recipe.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "evidentia_ai.eval.harness is deprecated; use evidentia_eval.harness. "
    "This shim will be removed in v0.12.0.",
    DeprecationWarning,
    stacklevel=2,
)

from evidentia_eval.harness import (  # noqa: E402
    DFAHarness,
    EvalResult,
    EvalSample,
    GeneratorFn,
)

__all__ = ["DFAHarness", "EvalResult", "EvalSample", "GeneratorFn"]
