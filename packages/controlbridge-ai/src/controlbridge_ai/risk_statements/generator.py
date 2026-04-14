"""Risk statement generator using LiteLLM + Instructor.

Generates NIST SP 800-30-compliant risk statements from control gaps
and system context. Uses Instructor for structured output extraction —
the LLM response is validated against the RiskStatement Pydantic model.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from controlbridge_core.models.gap import ControlGap
from controlbridge_core.models.risk import RiskStatement

from controlbridge_ai.client import (
    get_async_instructor_client,
    get_default_model,
    get_instructor_client,
    get_temperature,
)
from controlbridge_ai.risk_statements.prompts import (
    RISK_CONTEXT_TEMPLATE,
    RISK_STATEMENT_SYSTEM_PROMPT,
)
from controlbridge_ai.risk_statements.templates import SystemContext

logger = logging.getLogger(__name__)


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

    Usage:
        generator = RiskStatementGenerator(model="gpt-4o")

        # Single gap
        risk = generator.generate(gap=my_gap, system_context=my_context)

        # Batch
        risks = generator.generate_batch(
            gaps=report.gaps[:10],
            system_context=my_context,
        )
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

    def generate(
        self,
        gap: ControlGap,
        system_context: SystemContext,
    ) -> RiskStatement:
        """Generate a single risk statement for a control gap.

        Uses Instructor to extract a validated RiskStatement from the LLM response.
        If the LLM returns invalid JSON, Instructor automatically retries up to
        max_retries times.
        """
        user_prompt = _build_risk_context(gap, system_context)

        logger.info(
            "Generating risk statement for %s:%s using model=%s",
            gap.framework,
            gap.control_id,
            self.model,
        )

        risk: RiskStatement = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RISK_STATEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_model=RiskStatement,
            max_retries=self.max_retries,
            temperature=self.temperature,
        )

        # Enrich with metadata
        risk.source_gap_id = gap.id
        risk.model_used = self.model
        risk.framework_mappings = [
            f"{gap.framework}:{gap.control_id}",
            *gap.cross_framework_value,
        ]

        logger.info(
            "Generated risk statement: level=%s, priority=%s",
            risk.risk_level,
            risk.remediation_priority,
        )
        return risk

    def generate_batch(
        self,
        gaps: list[ControlGap],
        system_context: SystemContext,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[RiskStatement]:
        """Generate risk statements for multiple gaps sequentially.

        For concurrent batch processing, use generate_batch_async.

        Args:
            gaps: Control gaps to generate risk statements for
            system_context: System context for the organization
            on_progress: Optional callback(current, total) for progress reporting
        """
        results: list[RiskStatement] = []
        total = len(gaps)

        for i, gap in enumerate(gaps):
            try:
                risk = self.generate(gap, system_context)
                results.append(risk)
            except Exception as e:
                logger.error("Failed to generate risk for %s: %s", gap.control_id, e)
                continue

            if on_progress:
                on_progress(i + 1, total)

        logger.info(
            "Batch complete: %d/%d risk statements generated", len(results), total
        )
        return results

    async def generate_async(
        self,
        gap: ControlGap,
        system_context: SystemContext,
    ) -> RiskStatement:
        """Async version of generate() for concurrent batch processing."""
        client = get_async_instructor_client()
        user_prompt = _build_risk_context(gap, system_context)

        risk: RiskStatement = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RISK_STATEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_model=RiskStatement,
            max_retries=self.max_retries,
            temperature=self.temperature,
        )

        risk.source_gap_id = gap.id
        risk.model_used = self.model
        risk.framework_mappings = [
            f"{gap.framework}:{gap.control_id}",
            *gap.cross_framework_value,
        ]

        return risk

    async def generate_batch_async(
        self,
        gaps: list[ControlGap],
        system_context: SystemContext,
        max_concurrent: int = 5,
    ) -> list[RiskStatement]:
        """Async batch generation with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _generate_one(gap: ControlGap) -> RiskStatement | None:
            async with semaphore:
                try:
                    return await self.generate_async(gap, system_context)
                except Exception as e:
                    logger.error("Failed: %s: %s", gap.control_id, e)
                    return None

        tasks = [_generate_one(g) for g in gaps]
        raw_results = await asyncio.gather(*tasks)
        results: list[RiskStatement] = [r for r in raw_results if r is not None]

        logger.info("Async batch: %d/%d generated", len(results), len(gaps))
        return results
