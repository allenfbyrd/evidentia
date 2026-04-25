"""Typed exception hierarchy + shared transient-exception set for evidentia-ai (v0.7.1).

Replaces the bare ``except Exception`` patterns from v0.4.0 with a
narrow, intentional hierarchy so downstream callers can distinguish:

- **transient infrastructure failures** (network blip, rate limit) →
  :class:`LLMUnavailableError`. Caller may decide to retry the whole
  batch later, queue for the next run, or surface as a soft warning.
- **structural validation failures** (LLM returned JSON that doesn't
  conform to the response schema even after Instructor's bounded
  retries) → :class:`LLMValidationError`. Caller likely needs to log
  the offending response and skip the input — retrying won't help.
- **subsystem-specific generation failures** → subclasses of
  :class:`RiskStatementError` (risk_statements module) and (in PR #3)
  :class:`ExplainError` (explain module). Catch-all for anything that
  isn't transient or validation-shaped.

Air-gap policy violations
(:class:`evidentia_core.network_guard.OfflineViolationError`) are
deliberately NOT in this hierarchy. They are programmer/policy errors
that must propagate unchanged so operators see them immediately.
"""

from __future__ import annotations

import litellm.exceptions as _litellm_exc

# LiteLLM exceptions that indicate a transient infrastructure failure
# worth retrying. Programmer/policy errors (AuthenticationError,
# BadRequestError, NotFoundError, ContentPolicyViolationError,
# BudgetExceededError) are deliberately excluded \u2014 retrying won't help.
# Shared between risk_statements/ and explain/ so both subsystems retry
# on identical conditions.
LLM_TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    _litellm_exc.RateLimitError,
    _litellm_exc.APIConnectionError,
    _litellm_exc.Timeout,
    _litellm_exc.InternalServerError,
    _litellm_exc.ServiceUnavailableError,
    _litellm_exc.BadGatewayError,
)


class EvidentiaAIError(Exception):
    """Base exception for any evidentia-ai generation failure.

    Catch this when you want to handle ANY AI failure mode uniformly
    (e.g., a batch driver that wants to log-and-continue on every
    per-item failure regardless of cause).
    """


class LLMUnavailableError(EvidentiaAIError):
    """LLM endpoint unreachable / rate-limited / 5xx after retries.

    Wraps the underlying transient exception (LiteLLM ``RateLimitError``,
    ``APIConnectionError``, ``Timeout``, ``InternalServerError``,
    ``ServiceUnavailableError``, ``BadGatewayError``) after the
    configured ``@with_retry`` budget is exhausted. The original
    exception is preserved as ``__cause__``.
    """


class LLMValidationError(EvidentiaAIError):
    """LLM returned JSON that violates the response Pydantic model.

    Raised after Instructor's ``max_retries`` is exhausted — i.e., the
    LLM had multiple chances to produce conforming JSON and failed
    every time. The original ``InstructorRetryException`` is preserved
    as ``__cause__``.
    """


class RiskStatementError(EvidentiaAIError):
    """Base for any failure in the risk_statements subsystem.

    Catch this in :meth:`RiskStatementGenerator.generate_batch` (and
    its async sibling) to log-and-continue on per-gap failures while
    still completing the batch.
    """


class RiskGenerationFailed(RiskStatementError):
    """Catch-all for unexpected risk-statement generation failures.

    Wraps any exception that doesn't match the more specific cases —
    typically a programming bug (bad prompt template, model returning
    refusal text Instructor can't parse, etc.). The original exception
    is preserved as ``__cause__``.
    """


class ExplainError(EvidentiaAIError):
    """Base for any failure in the explain subsystem.

    Mirrors :class:`RiskStatementError`. Catch this in batch drivers
    (when added in a future release) to log-and-continue per-control.
    """


class ExplainGenerationFailed(ExplainError):
    """Catch-all for unexpected plain-English explanation failures.

    Mirrors :class:`RiskGenerationFailed`. Wraps any exception that
    doesn't match the more specific transient/validation cases.
    The original exception is preserved as ``__cause__``.
    """


__all__ = [
    "LLM_TRANSIENT_EXCEPTIONS",
    "EvidentiaAIError",
    "ExplainError",
    "ExplainGenerationFailed",
    "LLMUnavailableError",
    "LLMValidationError",
    "RiskGenerationFailed",
    "RiskStatementError",
]
