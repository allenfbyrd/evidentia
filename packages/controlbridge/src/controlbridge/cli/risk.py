"""`controlbridge risk` — AI risk statement generation."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="AI-powered risk statement generation.")
console = Console()


@app.command("generate")
def generate(
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

    console.print(f"[cyan]Loading system context from[/cyan] [bold]{context}[/bold]...")
    sys_ctx = SystemContext.from_yaml(context)
    console.print(
        f"[green]Loaded:[/green] {sys_ctx.organization} / {sys_ctx.system_name}"
    )

    if not gaps:
        console.print(
            "[yellow]Note: --gap-id without --gaps is not yet implemented "
            "(needs a persistent gap store).[/yellow]"
        )
        raise typer.Exit(code=1)

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
        f"[bold]{model or 'default'}[/bold]..."
    )

    generator = RiskStatementGenerator(model=model)

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
