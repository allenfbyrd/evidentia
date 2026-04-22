"""Generate plain-English explanations for compliance controls using an LLM."""

from __future__ import annotations

import logging
from pathlib import Path

import litellm
from evidentia_core.models.catalog import CatalogControl

from evidentia_ai.client import (
    get_default_model,
    get_instructor_client,
    get_temperature,
)
from evidentia_ai.explain.cache import load_cached, store
from evidentia_ai.explain.models import PlainEnglishExplanation

logger = logging.getLogger(__name__)


EXPLAIN_SYSTEM_PROMPT = """\
You are a compliance translator. Your job is to take control text written for
compliance auditors and policy writers — which is dense, formal, and written
for legal defensibility — and rewrite it so an engineer or executive can act
on it without a compliance specialist's help.

RULES for every field you produce:

1. Plain language. Zero acronyms without expansion. Zero jargon like "shall",
   "commensurate", "consistent with the foregoing".

2. Concrete over abstract. "Configure Okta" beats "Implement identity
   governance"; "Review IAM roles quarterly" beats "Perform periodic access
   review".

3. Honest about effort. If this control really requires a FedRAMP 3PAO and
   $200K of consulting time, say so. If it's a one-afternoon Terraform change,
   say so. Compliance teams lose trust when tooling pretends hard things are
   easy.

4. Threat-grounded. When explaining "why it matters", tie to a real-world
   attack pattern: credential stuffing, supply-chain compromise, insider
   exfil, ransomware lateral movement. Avoid abstract "maintain security
   posture" language.

5. Neutral on vendors. Don't recommend specific products unless the control
   genuinely names one (e.g., "FIPS 140-2 validated crypto modules"). "Your
   IdP" is fine; "Okta" is not fine unless Okta is actually the thing.
"""


def _build_user_prompt(control: CatalogControl, framework_id: str) -> str:
    desc = (control.description or "").strip() or "(no description in catalog)"
    family = f"\nFamily: {control.family}" if control.family else ""
    guidance = (
        f"\n\nOSCAL guidance:\n{control.guidance}"
        if getattr(control, "guidance", None)
        else ""
    )
    return (
        f"Framework: {framework_id}\n"
        f"Control ID: {control.id}\n"
        f"Control title: {control.title}{family}\n\n"
        f"Authoritative text:\n{desc}{guidance}\n\n"
        f"Produce a plain-English explanation following the system prompt rules. "
        f"Populate every field of the PlainEnglishExplanation schema."
    )


class ExplanationGenerator:
    """Plain-English explanation factory.

    Usage::

        gen = ExplanationGenerator(model="claude-sonnet-4", temperature=0.2)
        exp = gen.generate(control, framework_id="nist-800-53-rev5")

    Caching is on by default — repeated calls for the same
    ``(framework, control, model, temperature)`` tuple return the disk
    cache hit instantly. Pass ``use_cache=False`` to force a fresh
    generation, or call ``generate(..., refresh=True)``.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_retries: int = 3,
        use_cache: bool = True,
        cache_dir: Path | None = None,
    ) -> None:
        self.model = model or get_default_model()
        self.temperature = (
            temperature if temperature is not None else get_temperature()
        )
        self.max_retries = max_retries
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.client = get_instructor_client()

    def generate(
        self,
        control: CatalogControl,
        framework_id: str,
        refresh: bool = False,
    ) -> PlainEnglishExplanation:
        """Return an explanation, from cache if available."""
        if self.use_cache and not refresh:
            cached = load_cached(
                framework_id,
                control.id,
                self.model,
                self.temperature,
                cache_dir=self.cache_dir,
            )
            if cached is not None:
                logger.debug(
                    "Explain cache hit: %s:%s (model=%s)",
                    framework_id,
                    control.id,
                    self.model,
                )
                return cached

        prompt = _build_user_prompt(control, framework_id)
        logger.info(
            "Generating explanation for %s:%s using model=%s",
            framework_id,
            control.id,
            self.model,
        )

        explanation: PlainEnglishExplanation = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_model=PlainEnglishExplanation,
                max_retries=self.max_retries,
                temperature=self.temperature,
            )
        )

        # Enforce echo fields in case the LLM drifted
        explanation = explanation.model_copy(
            update={
                "framework_id": framework_id,
                "control_id": control.id,
                "control_title": control.title,
            }
        )

        if self.use_cache:
            store(
                explanation,
                self.model,
                self.temperature,
                cache_dir=self.cache_dir,
            )

        return explanation

    # Exposed so tests can stub without reaching into litellm internals.
    def _litellm_module(self):  # type: ignore[no-untyped-def]
        return litellm
