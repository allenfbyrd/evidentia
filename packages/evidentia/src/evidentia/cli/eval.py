"""``evidentia eval`` Typer subcommand group (v0.8.0 P0.1).

Wires the DFAH determinism harness to a CLI surface operators
+ CI pipelines can call directly. The flagship AI-quality
deliverable for v0.8.0 — auditor-defensible numerical proof
that the same prompt + model + temperature produces the same
output run-to-run.

One verb ships in v0.8.0:

- ``evidentia eval stub-smoke`` — run the harness against a
  built-in deterministic stub generator. Useful for validating
  the harness mechanics without burning LLM tokens; CI can
  invoke this verb to prove the eval surface stays wired even
  when LLM provider creds aren't available.

The library API (:class:`DFAHarness` + result models) is the
focal point — operators can wrap any generator function
(including :class:`RiskStatementGenerator.generate`) in a thin
callable today. The corpus-file schema + LiteLLM provider env
handshake for the CLI verb ``risk-determinism`` defers to
v0.8.1 alongside faithfulness scoring.

Future verbs (v0.8.1+): ``risk-determinism``,
``explain-determinism``, ``oscal-emit-determinism``,
``faithfulness``.

Per the secret-handling protocol, the CLI never accepts
LLM credentials in arguments — the LLM provider is read
from LiteLLM env vars by the underlying generator.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from evidentia_ai.eval import DFAHarness, EvalSample
from evidentia_core.audit.provenance import (
    GenerationContext,
    compute_prompt_hash,
)

app = typer.Typer(
    name="eval",
    help=(
        "DFAH determinism harness (v0.8.0 P0.1). Validates that "
        "AI-driven artifact generation is auditor-defensibly "
        "reproducible: same prompt + same model + same "
        "temperature produces the same output across N samples."
    ),
    no_args_is_help=True,
)


@app.callback()
def _eval_callback() -> None:
    """Marker callback — forces Typer to treat this as a subcommand
    group rather than collapsing the single-command app into a
    direct invocation."""


def _exit_per_threshold(
    overall_rate: float, threshold: float, output_path: Path | None
) -> None:
    """Exit 0 if rate >= threshold, 1 otherwise."""
    if overall_rate < threshold:
        typer.echo(
            f"Determinism rate {overall_rate:.4f} BELOW threshold "
            f"{threshold:.4f} — failing CI gate.",
            err=True,
        )
        if output_path is not None:
            typer.echo(
                f"Full per-prompt report: {output_path}", err=True
            )
        sys.exit(1)
    typer.echo(
        f"Determinism rate {overall_rate:.4f} >= threshold "
        f"{threshold:.4f} — PASS.",
    )


@app.command("stub-smoke")
def stub_smoke(
    samples_per_prompt: int = typer.Option(
        5,
        "--samples-per-prompt",
        "-n",
        help=(
            "Number of generation calls per prompt for the "
            "determinism check."
        ),
    ),
    fail_on_determinism_rate_below: float = typer.Option(
        0.95,
        "--fail-on-determinism-rate-below",
        help=(
            "Exit 1 if the overall determinism rate falls below "
            "this threshold. Default 0.95 (per arXiv 2601.15322 "
            "DFAH guidance)."
        ),
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Write the full :class:`EvalResult` JSON to this "
            "path. When omitted, only the summary line goes to "
            "stdout."
        ),
    ),
) -> None:
    """Run the harness against a built-in deterministic stub.

    Useful for CI smoke validation — proves the harness surface
    is wired without requiring LLM provider creds. Always
    passes (the stub is fully deterministic) unless the eval
    machinery itself has regressed.
    """

    def _stub_generator(prompt: str, _ctx: GenerationContext) -> str:
        # Deterministic — same input always produces same output.
        # The stub is intentionally trivial; the goal is to
        # exercise the harness loop, audit emit, and result-
        # serialization paths.
        return f"Stub risk statement for: {prompt}"

    def _make_ctx(prompt_id: str) -> GenerationContext:
        return GenerationContext(
            model="evidentia-stub",
            temperature=0.0,
            prompt_hash=compute_prompt_hash("stub-system", prompt_id),
        )

    samples = [
        EvalSample(
            prompt_id="smoke-AC-2",
            prompt=(
                "Generate a risk statement for control AC-2 "
                "(Account Management) at a fintech SaaS."
            ),
        ),
        EvalSample(
            prompt_id="smoke-AC-3",
            prompt=(
                "Generate a risk statement for control AC-3 "
                "(Access Enforcement) at a healthcare provider."
            ),
        ),
        EvalSample(
            prompt_id="smoke-CM-2",
            prompt=(
                "Generate a risk statement for control CM-2 "
                "(Baseline Configuration) at a financial-services "
                "firm."
            ),
        ),
    ]
    harness = DFAHarness(
        generator=_stub_generator,
        sample_count_per_prompt=samples_per_prompt,
    )
    result = harness.run(
        samples=samples,
        context_factory=_make_ctx,
        check_replay=True,
    )

    if output is not None:
        output.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    typer.echo(
        f"Eval run {result.run_id} — "
        f"{len(samples)} prompt(s), "
        f"{samples_per_prompt} sample(s) per prompt"
    )
    typer.echo(
        f"  • overall determinism rate: "
        f"{result.overall_determinism_rate:.4f}"
    )
    typer.echo(
        f"  • determinism violations: "
        f"{len(result.determinism_violations)}"
    )
    typer.echo(
        f"  • replay violations: "
        f"{len(result.replay_violations)}"
    )
    _exit_per_threshold(
        result.overall_determinism_rate,
        fail_on_determinism_rate_below,
        output,
    )


# NOTE: The ``risk-determinism`` verb (live LLM-driven harness
# against ``RiskStatementGenerator``) defers to v0.8.1. The
# library API (``DFAHarness`` + result models) ships in v0.8.0 —
# operators can wrap ``RiskStatementGenerator.generate`` in a
# thin callable from a Python script today. The CLI verb gets a
# proper corpus-file schema design + LiteLLM provider env
# handshake in v0.8.1 alongside the faithfulness scoring follow-
# up.
