"""``evidentia eval`` Typer subcommand group (v0.8.0 P0.1 + v0.8.1 P2.1).

Wires the DFAH determinism harness to a CLI surface operators
+ CI pipelines can call directly. The flagship AI-quality
deliverable for v0.8.0 — auditor-defensible numerical proof
that the same prompt + model + temperature produces the same
output run-to-run.

Two verbs ship in v0.8.1:

- ``evidentia eval stub-smoke`` — run the harness against a
  built-in deterministic stub generator. Useful for validating
  the harness mechanics without burning LLM tokens; CI can
  invoke this verb to prove the eval surface stays wired even
  when LLM provider creds aren't available.
- ``evidentia eval risk-determinism`` — run the harness
  against the live :class:`RiskStatementGenerator`. Loads a
  system context YAML + gap report JSON (same shape as
  ``evidentia risk generate``); fires N samples per gap;
  exits 1 if the overall determinism rate falls below the CI
  threshold.

The library API (:class:`DFAHarness` + result models) is the
focal point — operators can wrap any generator function in a
thin callable. The CLI verbs are thin orchestration on top
of that.

Future verbs (v0.8.x+): ``explain-determinism``,
``oscal-emit-determinism``, ``faithfulness``.

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


@app.command("risk-determinism")
def risk_determinism(
    context: Path = typer.Option(
        ...,
        "--context",
        "-c",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to system context YAML file (per `evidentia risk generate --context`).",
    ),
    gaps: Path = typer.Option(
        ...,
        "--gaps",
        "-g",
        exists=True,
        file_okay=True,
        readable=True,
        help="Path to a gap report JSON (from `evidentia gap analyze`).",
    ),
    gap_id: str | None = typer.Option(
        None,
        "--gap-id",
        help="Run determinism check against a single gap by ID (otherwise all gaps).",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Maximum number of gaps to process (post --gap-id filter).",
    ),
    samples_per_prompt: int = typer.Option(
        5,
        "--samples-per-prompt",
        help=(
            "Number of generation calls per gap. Each call is a "
            "live LLM round-trip; 5×N gaps × per-call latency = "
            "the wall-clock cost. Operators tune for their LLM "
            "provider rate-limits + token budget."
        ),
    ),
    fail_on_determinism_rate_below: float = typer.Option(
        0.95,
        "--fail-on-determinism-rate-below",
        help=(
            "Exit 1 if the overall determinism rate falls below "
            "this threshold. Default 0.95 per arXiv 2601.15322 "
            "DFAH guidance."
        ),
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Write the EvalResult JSON to this path. When "
            "omitted, only the summary line goes to stdout."
        ),
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help=(
            "LiteLLM model identifier passed through to "
            "RiskStatementGenerator. Defaults to whatever the "
            "EVIDENTIA_LLM_MODEL env var or evidentia.yaml "
            "specifies."
        ),
    ),
    temperature: float | None = typer.Option(
        None,
        "--temperature",
        help=(
            "Sampling temperature. 0.0 maximises determinism; "
            "the harness will report violations if the LLM "
            "provider is non-deterministic at this temperature."
        ),
    ),
    check_replay: bool = typer.Option(
        False,
        "--check-replay",
        help=(
            "Additionally run a single replay-equivalence pass "
            "per gap (re-uses the determinism context)."
        ),
    ),
) -> None:
    """Run the DFAH harness against the live RiskStatementGenerator.

    Loads the system context + gap report (same shape as
    ``evidentia risk generate``), wires
    :meth:`RiskStatementGenerator.generate` into the harness as
    the per-call generator, and exits 1 if the overall
    determinism rate falls below the CI threshold.

    Each per-gap output is the canonical-JSON model_dump of the
    LLM-returned ``RiskStatement``. Two outputs hash identically
    iff every field of the model serialized identically (modulo
    the v0.8.0 P0.1 normalization). This is stricter than
    "semantic equivalence" by design — auditors want a
    reproducibility guarantee, not a paraphrase-similarity
    estimate.

    Requires the LLM provider env vars matching the configured
    model (e.g., ``ANTHROPIC_API_KEY`` for ``claude-sonnet-4``,
    ``OPENAI_API_KEY`` for ``gpt-4o``, ``OLLAMA_HOST`` for a
    local Ollama endpoint). The harness never accepts
    credentials in arguments per the secret-handling protocol.

    Faithfulness scoring (the second arXiv-2601.15322 metric)
    is reserved for v0.8.x; this verb covers determinism +
    replay equivalence only.
    """
    # Lazy-import the LLM stack so the rest of `evidentia eval`
    # stays usable when LiteLLM/Instructor have transient init
    # failures (e.g., a malformed env var).
    import json as _json

    from evidentia_ai.risk_statements import (
        RiskStatementGenerator,
        SystemContext,
    )
    from evidentia_core.models.gap import ControlGap, GapAnalysisReport

    # Load the gap report.
    try:
        report = GapAnalysisReport.model_validate(
            _json.loads(gaps.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        typer.echo(f"Error loading gap report at {gaps}: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    # Load the system context.
    try:
        sys_ctx = SystemContext.from_yaml(context)
    except Exception as exc:
        typer.echo(
            f"Error loading system context at {context}: {exc}",
            err=True,
        )
        raise typer.Exit(code=2) from exc

    # Filter target gaps.
    target_gaps: list[ControlGap] = list(report.gaps)
    if gap_id:
        target_gaps = [g for g in target_gaps if g.id == gap_id]
        if not target_gaps:
            typer.echo(f"No gap found with id={gap_id}", err=True)
            raise typer.Exit(code=2)
    if limit:
        target_gaps = target_gaps[:limit]
    if not target_gaps:
        typer.echo("No gaps to evaluate.", err=True)
        raise typer.Exit(code=2)

    # Build the prompt_id → ControlGap index. Use
    # ``framework:control_id`` as a stable, human-readable
    # identifier (matches the conventional gap-label pattern).
    samples_by_id: dict[str, ControlGap] = {}
    eval_samples: list[EvalSample] = []
    for gap in target_gaps:
        prompt_id = f"{gap.framework}:{gap.control_id}"
        # Disambiguate if multiple gaps share framework+control
        # (rare but possible — e.g., the same control assessed
        # against two different system contexts in one report).
        suffix = 1
        candidate = prompt_id
        while candidate in samples_by_id:
            suffix += 1
            candidate = f"{prompt_id}#{suffix}"
        samples_by_id[candidate] = gap
        # EvalSample.prompt = prompt_id; the harness uses prompt
        # as a hash-comparison key + as the lookup index for
        # this generator wrapper (see _live_generator below).
        eval_samples.append(
            EvalSample(prompt_id=candidate, prompt=candidate)
        )

    # Build the live generator. RiskStatementGenerator() reads
    # model + temperature from EVIDENTIA_LLM_MODEL /
    # EVIDENTIA_LLM_TEMPERATURE env vars + evidentia.yaml when
    # the constructor args are None — match `evidentia risk
    # generate` precedence.
    try:
        generator = RiskStatementGenerator(
            model=model, temperature=temperature
        )
    except Exception as exc:
        typer.echo(
            f"RiskStatementGenerator construction failed: "
            f"{type(exc).__name__}: {exc}",
            err=True,
        )
        raise typer.Exit(code=2) from exc

    def _live_generator(
        prompt: str, _ctx: GenerationContext
    ) -> str:
        # ``prompt`` is the prompt_id (we set EvalSample.prompt =
        # prompt_id). Look up the structured ControlGap.
        gap = samples_by_id[prompt]
        risk_stmt = generator.generate(gap, sys_ctx)
        # Canonical JSON for hash comparison. The harness's
        # normalize_for_determinism + hash_output handles
        # whitespace + trailing-punct invariance; field-level
        # invariance is implicit in Pydantic's deterministic
        # model_dump_json.
        return risk_stmt.model_dump_json()

    def _make_ctx(prompt_id: str) -> GenerationContext:
        return GenerationContext(
            model=model or "evidentia-default",
            temperature=temperature if temperature is not None else 0.0,
            prompt_hash=compute_prompt_hash(
                "risk-statement-system", prompt_id
            ),
        )

    harness = DFAHarness(
        generator=_live_generator,
        sample_count_per_prompt=samples_per_prompt,
    )

    typer.echo(
        f"DFAH risk-determinism: {len(eval_samples)} gap(s), "
        f"{samples_per_prompt} sample(s) per gap → "
        f"{len(eval_samples) * samples_per_prompt} total LLM "
        f"calls"
    )
    if check_replay:
        typer.echo(
            f"  • plus {len(eval_samples)} replay calls"
        )

    result = harness.run(
        samples=eval_samples,
        context_factory=_make_ctx,
        check_replay=check_replay,
    )

    if output is not None:
        output.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    typer.echo(
        f"Eval run {result.run_id} — "
        f"{len(eval_samples)} gap(s)"
    )
    typer.echo(
        f"  • overall determinism rate: "
        f"{result.overall_determinism_rate:.4f}"
    )
    typer.echo(
        f"  • determinism violations: "
        f"{len(result.determinism_violations)}"
    )
    if check_replay:
        typer.echo(
            f"  • replay violations: "
            f"{len(result.replay_violations)}"
        )
    _exit_per_threshold(
        result.overall_determinism_rate,
        fail_on_determinism_rate_below,
        output,
    )
