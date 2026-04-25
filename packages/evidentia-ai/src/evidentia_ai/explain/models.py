"""Pydantic model for plain-English control explanations.

Schema is intentionally tight — Instructor uses this as the output
schema for the LLM, so drift here directly changes what the model is
asked to produce.
"""

from __future__ import annotations

from evidentia_core.audit.provenance import GenerationContext
from pydantic import BaseModel, ConfigDict, Field


class PlainEnglishExplanation(BaseModel):
    """Engineer-and-exec-friendly translation of a compliance control.

    Populated by :class:`ExplanationGenerator`. Every field is required so
    the LLM can't silently skip one; Instructor's validation + retry will
    regenerate on partial output.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # The source control being explained — echoed for provenance.
    framework_id: str = Field(description="Framework ID (e.g. 'nist-800-53-rev5')")
    control_id: str = Field(description="Control ID within the framework")
    control_title: str = Field(description="Control title from the catalog")

    # The actual explanation, structured for audience-specific rendering.
    plain_english: str = Field(
        description=(
            "1-2 sentence summary of what this control requires in plain "
            "English. No jargon, no quoting the NIST text verbatim."
        ),
        min_length=40,
    )
    why_it_matters: str = Field(
        description=(
            "1 paragraph explaining the threat this control mitigates and "
            "the business impact if an attacker exploited the gap. Anchored "
            "to real-world attack patterns where possible (former-employee "
            "credentials, supply-chain attacks, ransomware, etc)."
        ),
        min_length=80,
    )
    what_to_do: list[str] = Field(
        description=(
            "Bullet list of concrete implementation steps. Each bullet should "
            "be actionable by an engineer or IT admin — 'document a policy' "
            "or 'configure Okta group policy X'. 3-8 bullets."
        ),
        min_length=3,
        max_length=8,
    )
    effort_estimate: str = Field(
        description=(
            "Free-form effort estimate — e.g., 'Medium — requires policy "
            "documentation + quarterly review calendar + IAM tooling for "
            "orgs over 50 users'. Calibrate to the actual-implementation-"
            "team perspective, not compliance-writer perspective."
        ),
        min_length=20,
    )
    common_misconceptions: str | None = Field(
        default=None,
        description=(
            "Optional paragraph — common misreadings of the control's intent. "
            "For example: 'this control doesn't require encryption in transit, "
            "it requires network segmentation — which is different.'"
        ),
    )
    generation_context: GenerationContext | None = Field(
        default=None,
        description=(
            "v0.7.1+ AI provenance block. Optional in v0.7.x to preserve "
            "deserialization compat with cached pre-v0.7.1 explanations and "
            "v0.7.0 PlainEnglishExplanation payloads; will be tightened to "
            "required in v0.8 with a deprecation cycle. NOT minted on cache "
            "hits \u2014 the cached value (if any) is preserved verbatim. See "
            "``evidentia_core.audit.provenance.GenerationContext``."
        ),
    )
