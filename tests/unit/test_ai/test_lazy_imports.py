"""Lazy-import posture tests for evidentia_ai (v0.10.5 P9).

The Kimi engineering audit flagged a concern that ``import
evidentia_ai`` might top-level-load torch / transformers /
sentence-transformers, which would break air-gap installs of
the production risk-statement runtime.

This test pins the lazy-import posture in CI so a future
refactor doesn't accidentally regress. The assertion is
load-bearing: if any of the heavy ML deps ever creep into the
top-level import path of ``evidentia_ai``, this test fails
loudly.

The v0.10.5 P9 extraction (DFAH harness moved into
``evidentia-eval``) also relies on this contract: the
deprecation shim ``evidentia_ai.eval`` re-exports from
``evidentia_eval`` but must not be triggered by a bare
``import evidentia_ai``.
"""

from __future__ import annotations

import subprocess
import sys


def _run_isolated(snippet: str) -> tuple[int, str, str]:
    """Run ``snippet`` in a fresh Python subprocess.

    Returns ``(returncode, stdout, stderr)``. A fresh process is
    required because pytest itself may already have imported the
    relevant heavy deps via fixtures, collection, or other tests.
    """
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_evidentia_ai_top_level_does_not_load_torch() -> None:
    """``import evidentia_ai`` must NOT pull torch into sys.modules."""
    rc, out, err = _run_isolated(
        "import sys; import evidentia_ai; "
        "assert 'torch' not in sys.modules, "
        "'torch leaked into evidentia_ai top-level import'"
    )
    assert rc == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"


def test_evidentia_ai_top_level_does_not_load_transformers() -> None:
    """``import evidentia_ai`` must NOT pull transformers into sys.modules."""
    rc, out, err = _run_isolated(
        "import sys; import evidentia_ai; "
        "assert 'transformers' not in sys.modules, "
        "'transformers leaked into evidentia_ai top-level import'"
    )
    assert rc == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"


def test_evidentia_ai_top_level_does_not_load_sentence_transformers() -> None:
    """``import evidentia_ai`` must NOT pull sentence_transformers."""
    rc, out, err = _run_isolated(
        "import sys; import evidentia_ai; "
        "assert 'sentence_transformers' not in sys.modules, "
        "'sentence_transformers leaked into evidentia_ai top-level "
        "import'"
    )
    assert rc == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"


def test_evidentia_ai_top_level_does_not_load_evidentia_harness() -> None:
    """``import evidentia_ai`` must NOT trigger the harness shim.

    The v0.10.5 P9 deprecation shim re-exports from
    ``evidentia_eval``. The shim fires a ``DeprecationWarning``
    at import time, so accidentally pulling it on every
    ``import evidentia_ai`` would be both a correctness
    regression (warnings every air-gap install) and a
    performance regression (loads the whole harness stack).
    """
    rc, out, err = _run_isolated(
        "import sys; import evidentia_ai; "
        "assert 'evidentia_eval' not in sys.modules, "
        "'evidentia_eval leaked into evidentia_ai top-level import'"
    )
    assert rc == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"


def test_evidentia_ai_risk_statements_does_not_load_harness_stack() -> None:
    """Production risk-statement runtime must not pull the harness stack.

    Air-gap deploys typically pull ``from evidentia_ai.risk_statements
    import RiskStatementGenerator``. That code path is production
    runtime; it must not transitively load sentence-transformers,
    numpy, or the DFAH harness.
    """
    rc, out, err = _run_isolated(
        "import sys; "
        "from evidentia_ai.risk_statements import RiskStatementGenerator; "
        "assert 'evidentia_eval' not in sys.modules, "
        "'evidentia_eval leaked into evidentia_ai.risk_statements'; "
        "assert 'sentence_transformers' not in sys.modules, "
        "'sentence_transformers leaked into evidentia_ai.risk_statements'"
    )
    assert rc == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
