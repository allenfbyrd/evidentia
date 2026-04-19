"""`controlbridge risk` — AI risk statement generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="AI-powered risk statement generation.")
console = Console()


@app.command("generate")
def generate(
    ctx: typer.Context,
    context: Path = typer.Option(
        ...,
        "--context",
        "-c",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to system context YAML file.",
    ),
    gaps: Path | None = typer.Option(
        None,
        "--gaps",
        "-g",
        exists=True,
        file_okay=True,
        readable=True,
        help="Path to a gap report JSON (from `controlbridge gap analyze`).",
    ),
    gap_id: str | None = typer.Option(
        None,
        "--gap-id",
        help="Generate a risk statement for a single gap by ID.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model name (e.g. 'gpt-4o', 'claude-sonnet-4', 'ollama/llama3.3').",
    ),
    output: Path = typer.Option(
        Path("risks.json"),
        "--output",
        "-o",
        help="Output file path for generated risks.",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Maximum number of gaps to process.",
    ),
) -> None:
    """Generate NIST SP 800-30 risk statements for gaps using an LLM."""
    # Lazy import — avoid loading litellm/instructor unless this command is invoked
    from controlbridge_ai.risk_statements import RiskStatementGenerator, SystemContext
    from controlbridge_core.models.gap import GapAnalysisReport

    if not gaps and not gap_id:
        console.print(
            "[red]Error: must provide either --gaps or --gap-id.[/red]"
        )
        raise typer.Exit(code=1)

    # v0.2.1: resolve LLM model/temperature via config precedence:
    # CLI flag > env var > controlbridge.yaml > RiskStatementGenerator default.
    from controlbridge_core.config import ControlBridgeConfig, get_default

    cfg_obj = ctx.obj.get("config") if ctx.obj else None
    cfg: ControlBridgeConfig = cfg_obj if cfg_obj is not None else ControlBridgeConfig()
    resolved_model = get_default(
        cfg, model, "llm.model", env_var="CONTROLBRIDGE_LLM_MODEL"
    )
    # Temperature is harder to precedence via get_default (0.0 is falsy) —
    # do it explicitly. Flag > env > yaml.
    import contextlib

    resolved_temperature: float | None = None
    env_temp = os.environ.get("CONTROLBRIDGE_LLM_TEMPERATURE")
    if env_temp is not None:
        with contextlib.suppress(ValueError):
            resolved_temperature = float(env_temp)
    if resolved_temperature is None and cfg.llm.temperature is not None:
        resolved_temperature = cfg.llm.temperature

    console.print(f"[cyan]Loading system context from[/cyan] [bold]{context}[/bold]...")
    sys_ctx = SystemContext.from_yaml(context)
    console.print(
        f"[green]Loaded:[/green] {sys_ctx.organization} / {sys_ctx.system_name}"
    )

    # v0.2.1: when --gaps is omitted, load the most recent report from
    # the user-dir gap store (populated by every `gap analyze` run).
    # This is the pair to D4 in the v0.2.1 plan.
    if not gaps:
        from controlbridge_core.gap_store import load_latest_report

        report = load_latest_report()
        if report is None:
            console.print(
                "[red]No gap reports found in the store.[/red]\n"
                "[dim]Run `controlbridge gap analyze ...` first, or pass "
                "`--gaps <path>` to load a report explicitly.[/dim]"
            )
            raise typer.Exit(code=1)
        console.print(
            f"[cyan]Using latest gap report:[/cyan] {report.organization} "
            f"({report.total_gaps} gaps, {len(report.frameworks_analyzed)} frameworks)"
        )
    else:
        report_data = json.loads(gaps.read_text(encoding="utf-8"))
        report = GapAnalysisReport.model_validate(report_data)
    target_gaps = report.gaps

    if gap_id:
        target_gaps = [g for g in target_gaps if g.id == gap_id]
        if not target_gaps:
            console.print(f"[red]No gap found with id={gap_id}[/red]")
            raise typer.Exit(code=1)

    if limit:
        target_gaps = target_gaps[:limit]

    console.print(
        f"[cyan]Generating risk statements for[/cyan] "
        f"[bold]{len(target_gaps)}[/bold] gaps using model "
        f"[bold]{resolved_model or 'default'}[/bold]"
        + (
            f" @ temperature={resolved_temperature}"
            if resolved_temperature is not None
            else ""
        )
        + "..."
    )

    generator = RiskStatementGenerator(
        model=resolved_model, temperature=resolved_temperature
    )

    risks = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating...", total=len(target_gaps))
        for gap in target_gaps:
            try:
                risk = generator.generate(gap, sys_ctx)
                risks.append(risk)
            except Exception as e:
                console.print(
                    f"[red]Failed for {gap.control_id}: {e}[/red]"
                )
            progress.advance(task)

    # Write output
    output.write_text(
        json.dumps(
            [r.model_dump(mode="json") for r in risks],
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    console.print(
        f"[green]Generated[/green] {len(risks)}/{len(target_gaps)} risk statements"
    )
    console.print(f"[green]Output:[/green] [bold]{output}[/bold]")
