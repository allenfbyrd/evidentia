"""Risk statement generator using LiteLLM + Instructor.

Generates NIST SP 800-30-compliant risk statements from control gaps
and system context. Uses Instructor for structured output extraction —
the LLM response is validated against the RiskStatement Pydantic model.

v0.7.1 enterprise-grade refactor:

- Stdlib ``logging`` replaced with
  :func:`evidentia_core.audit.get_logger` for ECS-8.11 structured
  output.
- Every LLM call wrapped in bounded retry via
  :func:`evidentia_core.audit.build_retrying` /
  :func:`build_async_retrying` against the LiteLLM transient exception
  set (``RateLimitError``, ``APIConnectionError``, ``Timeout``,
  ``InternalServerError``, ``ServiceUnavailableError``,
  ``BadGatewayError``). Retry events tag as
  :attr:`~evidentia_core.audit.events.EventAction.AI_RISK_RETRY`.
- Bare ``except Exception`` (v0.4.0 BLOCKER B3, lines 173 + 227)
  replaced with the typed
  :class:`~evidentia_ai.exceptions.RiskStatementError` hierarchy.
- Every output carries a
  :class:`~evidentia_core.audit.provenance.GenerationContext` block so
  an auditor can reproduce the call (model, temperature, prompt_hash)
  and see retry counts.
- Air-gap policy violations
  (:class:`~evidentia_core.network_guard.OfflineViolationError`) are
  deliberately NOT swallowed — they propagate unchanged so operators
  see them immediately.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from evidentia_core.audit import (
    EventAction,
    EventOutcome,
    GenerationContext,
    build_async_retrying,
    build_retrying,
    compute_prompt_hash,
    get_logger,
    new_run_id,
)
from evidentia_core.models.gap import ControlGap
from evidentia_core.models.risk import RiskStatement
from evidentia_core.network_guard import OfflineViolationError
from instructor.core import InstructorRetryException

from evidentia_ai.client import (
    get_async_instructor_client,
    get_default_model,
    get_instructor_client,
    get_operator_identity,
    get_temperature,
)
from evidentia_ai.exceptions import (
    LLM_TRANSIENT_EXCEPTIONS as _LLM_TRANSIENT_EXCEPTIONS,
)
from evidentia_ai.exceptions import (
    LLMUnavailableError,
    LLMValidationError,
    RiskGenerationFailed,
    RiskStatementError,
)
from evidentia_ai.risk_statements.prompts import (
    RISK_CONTEXT_TEMPLATE,
    RISK_STATEMENT_SYSTEM_PROMPT,
)
from evidentia_ai.risk_statements.templates import SystemContext

_log = get_logger("evidentia.ai.risk_statements")


@contextmanager
def _no_scope() -> Iterator[None]:
    """No-op context manager used when no run_id is available to scope on."""
    yield


def _build_risk_context(gap: ControlGap, context: SystemContext) -> str:
    """Build the user prompt with full risk context."""
    components_text = ""
    for comp in context.components:
        components_text += f"- {comp.name} ({comp.type}): {comp.technology}"
        if comp.data_handled:
            components_text += f" — handles: {', '.join(comp.data_handled)}"
        if comp.location:
            components_text += f" — location: {comp.location}"
        components_text += "\n"

    threat_actors_text = (
        "\n".join(f"- {t}" for t in context.threat_actors) or "Not specified"
    )
    existing_controls_text = ", ".join(context.existing_controls) or "None specified"
    cross_fw_text = ", ".join(gap.cross_framework_value) or "None"

    severity_value = (
        gap.gap_severity.value
        if hasattr(gap.gap_severity, "value")
        else gap.gap_severity
    )

    return RISK_CONTEXT_TEMPLATE.format(
        organization=context.organization,
        system_name=context.system_name,
        system_description=context.system_description,
        data_classification=", ".join(context.data_classification),
        hosting=context.hosting,
        risk_tolerance=context.risk_tolerance,
        components_text=components_text.strip() or "Not specified",
        threat_actors_text=threat_actors_text,
        existing_controls_text=existing_controls_text,
        gap_framework=gap.framework,
        gap_control_id=gap.control_id,
        gap_control_title=gap.control_title,
        gap_control_description=gap.control_description,
        gap_severity=severity_value,
        gap_description=gap.gap_description,
        gap_implementation_status=gap.implementation_status,
        cross_framework_value=cross_fw_text,
    )


class RiskStatementGenerator:
    """Generates risk statements from control gaps using LLMs.

    Usage::

        generator = RiskStatementGenerator(model="gpt-4o")

        # Single gap
        risk = generator.generate(gap=my_gap, system_context=my_context)

        # Batch
        risks = generator.generate_batch(
            gaps=report.gaps[:10],
            system_context=my_context,
        )

    Every returned :class:`RiskStatement` carries a
    :class:`GenerationContext` block — see ``risk.generation_context``.

    Failure modes (v0.7.1):

    - :class:`LLMUnavailableError` — LiteLLM transient exception
      survived 3 retries (rate limit, network, 5xx).
    - :class:`LLMValidationError` — Instructor's validation retries
      were exhausted; LLM never produced conforming JSON.
    - :class:`RiskGenerationFailed` — anything else unexpected.
    - :class:`OfflineViolationError` — propagates unchanged when the
      configured model is a cloud model and air-gap mode is on.

    The batch entry points (:meth:`generate_batch`,
    :meth:`generate_batch_async`) catch
    :class:`RiskStatementError` (the parent of the first three above)
    and log-and-continue so a single bad gap doesn't abort the run.
    They do NOT catch :class:`OfflineViolationError` — air-gap
    violations abort the batch immediately.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_retries: int = 3,
    ) -> None:
        self.model = model or get_default_model()
        self.temperature = (
            temperature if temperature is not None else get_temperature()
        )
        self.max_retries = max_retries
        self.client = get_instructor_client()

    # ── LLM invocation helpers ────────────────────────────────────────
    #
    # Both helpers raise ONE OF:
    # - litellm.* transient exceptions (caller wraps as LLMUnavailableError)
    # - instructor.core.InstructorRetryException (caller wraps as LLMValidationError)
    # - OfflineViolationError (caller re-raises unchanged)
    # - any other Exception (caller wraps as RiskGenerationFailed)
    #
    # Returning the (RiskStatement, attempts) tuple lets the caller
    # populate GenerationContext.attempts with the actual count rather
    # than hard-coding 1.

    def _invoke_llm_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        run_id: str | None = None,
    ) -> tuple[RiskStatement, int]:
        retrying = build_retrying(
            function_name="risk_statement_generate",
            max_attempts=3,
            retry_on=_LLM_TRANSIENT_EXCEPTIONS,
            event_action=EventAction.AI_RISK_RETRY,
        )
        last_attempt = 0
        risk: RiskStatement | None = None
        # H2: scope retry events with the run_id so before_sleep emissions
        # in retry.py inherit trace.id = run_id (visible to SIEM correlation).
        # The structured logger's _scope_context is process-global, so the
        # tenacity callback's _log.warning(...) picks it up automatically.
        with _log.scope(trace_id=run_id) if run_id else _no_scope():
            for attempt in retrying:
                with attempt:
                    last_attempt = attempt.retry_state.attempt_number
                    risk = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_model=RiskStatement,
                        max_retries=self.max_retries,
                        temperature=self.temperature,
                    )
        # M1: tenacity reraise=True guarantees the loop either populates risk
        # or raises. An explicit raise survives -O (which strips asserts).
        if risk is None:
            raise RuntimeError(
                "Internal invariant violated: tenacity retry loop exited "
                "without populating risk and without raising. Indicates a "
                "tenacity behaviour change \u2014 review build_retrying()."
            )
        return risk, last_attempt

    async def _invoke_llm_async(
        self,
        system_prompt: str,
        user_prompt: str,
        run_id: str | None = None,
    ) -> tuple[RiskStatement, int]:
        client = get_async_instructor_client()
        retrying = build_async_retrying(
            function_name="risk_statement_generate_async",
            max_attempts=3,
            retry_on=_LLM_TRANSIENT_EXCEPTIONS,
            event_action=EventAction.AI_RISK_RETRY,
        )
        last_attempt = 0
        risk: RiskStatement | None = None
        with _log.scope(trace_id=run_id) if run_id else _no_scope():
            async for attempt in retrying:
                with attempt:
                    last_attempt = attempt.retry_state.attempt_number
                    risk = await client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_model=RiskStatement,
                        max_retries=self.max_retries,
                        temperature=self.temperature,
                    )
        if risk is None:
            raise RuntimeError(
                "Internal invariant violated: tenacity async retry loop "
                "exited without populating risk and without raising."
            )
        return risk, last_attempt

    def _build_generation_context(
        self,
        system_prompt: str,
        user_prompt: str,
        attempts: int,
        run_id: str | None = None,
    ) -> GenerationContext:
        return GenerationContext(
            model=self.model,
            temperature=self.temperature,
            prompt_hash=compute_prompt_hash(system_prompt, user_prompt),
            run_id=run_id if run_id is not None else new_run_id(),
            attempts=attempts,
            instructor_max_retries=self.max_retries,
            credential_identity=get_operator_identity(),
        )

    def _enrich(
        self,
        risk: RiskStatement,
        gap: ControlGap,
        gen_ctx: GenerationContext,
    ) -> RiskStatement:
        """Apply post-generation enrichment that the LLM doesn't produce."""
        risk.source_gap_id = gap.id
        risk.model_used = self.model
        risk.framework_mappings = [
            f"{gap.framework}:{gap.control_id}",
            *gap.cross_framework_value,
        ]
        risk.generation_context = gen_ctx
        return risk

    # ── Public API ────────────────────────────────────────────────────

    def generate(
        self,
        gap: ControlGap,
        system_context: SystemContext,
        run_id: str | None = None,
    ) -> RiskStatement:
        """Generate a single risk statement for a control gap.

        Network-layer transient failures are retried up to 3 times via
        ``@with_retry``. Validation failures (LLM returns malformed
        JSON) are retried up to ``self.max_retries`` times by Instructor.

        ``run_id`` is populated automatically per-call; pass an explicit
        run_id when threading a single batch identity through multiple
        calls (see :meth:`generate_batch` for the canonical pattern).
        """
        user_prompt = _build_risk_context(gap, system_context)
        gap_label = f"{gap.framework}:{gap.control_id}"

        try:
            risk, attempts = self._invoke_llm_sync(
                RISK_STATEMENT_SYSTEM_PROMPT, user_prompt, run_id=run_id
            )
        except OfflineViolationError:
            # Programmer/policy error — must surface to the operator.
            raise
        except _LLM_TRANSIENT_EXCEPTIONS as exc:
            self._emit_failure(gap_label, exc, "transient_after_retries", run_id)
            raise LLMUnavailableError(
                f"LLM transient error for {gap_label} after retries: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        except InstructorRetryException as exc:
            self._emit_failure(gap_label, exc, "validation_exhausted", run_id)
            raise LLMValidationError(
                f"Instructor validation retries exhausted for {gap_label}: {exc}"
            ) from exc
        except Exception as exc:
            self._emit_failure(gap_label, exc, "unexpected", run_id)
            raise RiskGenerationFailed(
                f"Unexpected risk-statement failure for {gap_label}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        gen_ctx = self._build_generation_context(
            RISK_STATEMENT_SYSTEM_PROMPT, user_prompt, attempts, run_id=run_id
        )
        risk = self._enrich(risk, gap, gen_ctx)
        self._emit_success(risk, gap_label, attempts)
        return risk

    def generate_batch(
        self,
        gaps: list[ControlGap],
        system_context: SystemContext,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[RiskStatement]:
        """Generate risk statements for multiple gaps sequentially.

        Per-gap :class:`RiskStatementError` failures are logged via
        ``AI_RISK_FAILED`` and skipped; the batch continues. Air-gap
        violations (:class:`OfflineViolationError`) abort the batch.

        Args:
            gaps: Control gaps to generate risk statements for
            system_context: System context for the organization
            on_progress: Optional callback(current, total) for progress reporting
        """
        results: list[RiskStatement] = []
        total = len(gaps)
        # One run_id for the entire batch — every output is tagged with
        # the same id so an auditor can reconstruct the batch from the
        # audit log via a single trace.id query.
        batch_run_id = new_run_id()

        for i, gap in enumerate(gaps):
            try:
                risk = self.generate(gap, system_context, run_id=batch_run_id)
                results.append(risk)
            except RiskStatementError:
                # Already emitted AI_RISK_FAILED inside .generate(); just
                # continue to the next gap. The base class catches all of
                # LLMUnavailableError, LLMValidationError, RiskGenerationFailed.
                continue

            if on_progress:
                on_progress(i + 1, total)

        # M4: outcome = SUCCESS only when every gap succeeded; UNKNOWN when
        # some failed (per ECS spec, UNKNOWN is the partial-success signal).
        # M2: distinct event action prevents per-call + summary double-counting.
        batch_outcome = (
            EventOutcome.SUCCESS if len(results) == total else EventOutcome.UNKNOWN
        )
        _log.info(
            action=EventAction.AI_RISK_BATCH_COMPLETED,
            outcome=batch_outcome,
            message=f"Batch complete: {len(results)}/{total} risk statements generated",
            evidentia={
                "run_id": batch_run_id,
                "model": self.model,
                "succeeded": len(results),
                "total": total,
                "failed": total - len(results),
            },
        )
        return results

    async def generate_async(
        self,
        gap: ControlGap,
        system_context: SystemContext,
        run_id: str | None = None,
    ) -> RiskStatement:
        """Async version of :meth:`generate` for concurrent batch processing."""
        user_prompt = _build_risk_context(gap, system_context)
        gap_label = f"{gap.framework}:{gap.control_id}"

        try:
            risk, attempts = await self._invoke_llm_async(
                RISK_STATEMENT_SYSTEM_PROMPT, user_prompt, run_id=run_id
            )
        except OfflineViolationError:
            raise
        except _LLM_TRANSIENT_EXCEPTIONS as exc:
            self._emit_failure(gap_label, exc, "transient_after_retries", run_id)
            raise LLMUnavailableError(
                f"LLM transient error for {gap_label} after retries: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        except InstructorRetryException as exc:
            self._emit_failure(gap_label, exc, "validation_exhausted", run_id)
            raise LLMValidationError(
                f"Instructor validation retries exhausted for {gap_label}: {exc}"
            ) from exc
        except Exception as exc:
            self._emit_failure(gap_label, exc, "unexpected", run_id)
            raise RiskGenerationFailed(
                f"Unexpected risk-statement failure for {gap_label}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        gen_ctx = self._build_generation_context(
            RISK_STATEMENT_SYSTEM_PROMPT, user_prompt, attempts, run_id=run_id
        )
        risk = self._enrich(risk, gap, gen_ctx)
        self._emit_success(risk, gap_label, attempts)
        return risk

    async def generate_batch_async(
        self,
        gaps: list[ControlGap],
        system_context: SystemContext,
        max_concurrent: int = 5,
    ) -> list[RiskStatement]:
        """Async batch generation with concurrency control.

        Per-gap :class:`RiskStatementError` failures are logged and the
        gap is dropped from the result list. Air-gap violations
        propagate and abort the batch.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        batch_run_id = new_run_id()

        async def _generate_one(gap: ControlGap) -> RiskStatement | None:
            async with semaphore:
                try:
                    return await self.generate_async(
                        gap, system_context, run_id=batch_run_id
                    )
                except RiskStatementError:
                    return None

        tasks = [_generate_one(g) for g in gaps]
        raw_results = await asyncio.gather(*tasks)
        results: list[RiskStatement] = [r for r in raw_results if r is not None]

        batch_outcome = (
            EventOutcome.SUCCESS
            if len(results) == len(gaps)
            else EventOutcome.UNKNOWN
        )
        _log.info(
            action=EventAction.AI_RISK_BATCH_COMPLETED,
            outcome=batch_outcome,
            message=(
                f"Async batch complete: {len(results)}/{len(gaps)} "
                f"risk statements generated"
            ),
            evidentia={
                "run_id": batch_run_id,
                "model": self.model,
                "succeeded": len(results),
                "total": len(gaps),
                "failed": len(gaps) - len(results),
                "max_concurrent": max_concurrent,
            },
        )
        return results

    # ── Structured event helpers ──────────────────────────────────────

    def _emit_success(
        self, risk: RiskStatement, gap_label: str, attempts: int
    ) -> None:
        gen_ctx = risk.generation_context
        _log.info(
            action=EventAction.AI_RISK_GENERATED,
            outcome=EventOutcome.SUCCESS,
            message=(
                f"Generated risk statement for {gap_label} "
                f"(level={risk.risk_level}, priority={risk.remediation_priority}, "
                f"attempts={attempts})"
            ),
            evidentia={
                "model": self.model,
                "gap_label": gap_label,
                "risk_level": str(risk.risk_level),
                "remediation_priority": risk.remediation_priority,
                "attempts": attempts,
                # H1+L2: surface run_id and prompt_hash so SIEM can join the
                # log event to the artifact-level GenerationContext block.
                "run_id": gen_ctx.run_id if gen_ctx is not None else None,
                "prompt_hash": gen_ctx.prompt_hash if gen_ctx is not None else None,
            },
        )

    def _emit_failure(
        self,
        gap_label: str,
        exc: BaseException,
        failure_kind: str,
        run_id: str | None = None,
    ) -> None:
        _log.error(
            action=EventAction.AI_RISK_FAILED,
            outcome=EventOutcome.FAILURE,
            message=(
                f"Risk-statement generation failed for {gap_label} "
                f"({failure_kind}): {type(exc).__name__}: {exc}"
            ),
            error={
                "type": type(exc).__name__,
                "message": str(exc),
            },
            evidentia={
                "model": self.model,
                "gap_label": gap_label,
                "failure_kind": failure_kind,
                # H1: thread the batch run_id into failure events so SIEM
                # queries on evidentia.run_id surface successes AND failures.
                "run_id": run_id,
            },
        )
