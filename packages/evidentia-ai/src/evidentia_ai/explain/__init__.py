"""Plain-English control explanations (v0.3.0).

Translates compliance-framework control text (NIST, HIPAA, CMMC, etc.) —
which is written for policy experts — into concrete guidance engineers
and executives can act on. Leverages the existing LiteLLM + Instructor
stack so any LLM provider works.

Usage::

    from evidentia_ai.explain import ExplanationGenerator
    from evidentia_core.catalogs.registry import FrameworkRegistry

    reg = FrameworkRegistry.get_instance()
    ctrl = reg.get_control("nist-800-53-rev5", "AC-2")
    gen = ExplanationGenerator()
    exp = gen.generate(ctrl, framework_id="nist-800-53-rev5")
    print(exp.plain_english)
"""

from evidentia_ai.explain.generator import ExplanationGenerator
from evidentia_ai.explain.models import PlainEnglishExplanation

__all__ = ["ExplanationGenerator", "PlainEnglishExplanation"]
