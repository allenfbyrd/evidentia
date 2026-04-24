"""Bounded retry with exponential backoff + jitter (v0.7.0).

Implements checklist item B10: every API call made by a collector must
be wrapped in bounded retry logic so transient source-system failures
don't produce silent evidence gaps.

Design principles:

- **Bounded by attempts, not time.** Unbounded retry loops are a
  denial-of-service vector against source systems. Default cap is 5.
- **Exponential backoff with full jitter.** tenacity's
  ``wait_exponential_jitter`` applies full jitter per the AWS
  Architecture Blog guidance.
- **Structured logging on every retry.** Every retry emits a
  :attr:`~evidentia_core.audit.events.EventAction.COLLECT_RETRY` event.
- **Test-mode short-circuit.** When ``EVIDENTIA_TEST_MODE=1`` is set,
  backoff is zeroed so retry-heavy tests don't burn wall-clock time.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from evidentia_core.audit.events import EventAction, EventOutcome
from evidentia_core.audit.logger import get_logger

P = ParamSpec("P")
R = TypeVar("R")

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 60.0
TEST_MODE_ENV = "EVIDENTIA_TEST_MODE"

_log = get_logger("evidentia.audit.retry")


def with_retry(
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF_SECONDS,
    max_backoff: float = DEFAULT_MAX_BACKOFF_SECONDS,
    retry_on: tuple[type[BaseException], ...] = (
        ConnectionError,
        TimeoutError,
    ),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator adding bounded exponential-backoff retry to a function.

    The wrapped function's signature is preserved. On the final failed
    attempt, the last exception is re-raised.
    """

    if os.environ.get(TEST_MODE_ENV):
        effective_initial = 0.0
        effective_max = 0.0
    else:
        effective_initial = initial_backoff
        effective_max = max_backoff

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            retrying = Retrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential_jitter(
                    initial=effective_initial,
                    max=effective_max,
                ),
                retry=retry_if_exception_type(retry_on),
                before_sleep=_log_retry_event(fn.__name__, max_attempts),
                reraise=True,
            )
            for attempt in retrying:
                with attempt:
                    return fn(*args, **kwargs)
            raise RuntimeError("unreachable")

        return wrapper

    return decorator


def _log_retry_event(
    function_name: str, max_attempts: int
) -> Callable[[RetryCallState], None]:
    """Build a tenacity ``before_sleep`` callback emitting retry events."""

    def _callback(retry_state: RetryCallState) -> None:
        attempt_number = retry_state.attempt_number
        exc: BaseException | None = None
        if retry_state.outcome is not None:
            exc = retry_state.outcome.exception()

        _log.warning(
            action=EventAction.COLLECT_RETRY,
            outcome=EventOutcome.FAILURE,
            message=(
                # Tenacity invokes ``before_sleep`` AFTER an attempt
                # fails and BEFORE the next attempt starts, so
                # ``attempt_number`` is the one that just failed.
                f"{function_name} attempt {attempt_number}/{max_attempts} "
                f"failed with {type(exc).__name__ if exc else 'unknown'}; "
                f"retrying"
            ),
            error=(
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                if exc
                else None
            ),
            evidentia={
                "function": function_name,
                "attempt": attempt_number,
                "max_attempts": max_attempts,
            },
        )

    return _callback


def is_test_mode() -> bool:
    """Return True iff :envvar:`EVIDENTIA_TEST_MODE` is set to a truthy value."""
    value = os.environ.get(TEST_MODE_ENV, "")
    return value.lower() not in ("", "0", "false", "no")


__all__ = [
    "DEFAULT_INITIAL_BACKOFF_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "TEST_MODE_ENV",
    "is_test_mode",
    "with_retry",
]
