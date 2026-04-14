"""`controlbridge gap` — gap analysis commands."""

from __future__ import annotations

from pathlib import Path

import typer
from controlbridge_core.gap_analyzer import GapAnalyzer, export_report, load_inventory
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Gap analysis commands.")
console = Console()


@app.command("analyze")
def analyze(
    inventory: Path = typer.Option(
        ...,
        "--inventory",
        "-i",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to control inventory (YAML, CSV, or JSON).",
    ),
    frameworks: str = typer.Option(
        ...,
        "--frameworks",
        "-f",
        help="Comma-separated framework IDs, e.g. 'nist-800-53-mod,soc2-tsc'.",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output file path for the report.",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json, csv, markdown, oscal-ar.",
    ),
    show_efficiency_opportunities: bool = typer.Option(
        True,
        "--show-efficiency-opportunities/--no-efficiency",
        help="Include cross-framework efficiency analysis.",
    ),
    min_efficiency_frameworks: int = typer.Option(
        3,
        "--min-efficiency-frameworks",
        help="Minimum frameworks for an efficiency opportunity.",
    ),
) -> None:
    """Run gap analysis against one or more frameworks."""
    framework_list = [f.strip() for f in frameworks.split(",") if f.strip()]

    console.print(
        f"[cyan]Loading inventory from[/cyan] [bold]{inventory}[/bold]..."
    )
    inv = load_inventory(inventory)
    console.print(
        f"[green]Loaded[/green] {len(inv.controls)} controls for "
        f"[bold]{inv.organization}[/bold]"
    )

    console.print(
        f"[cyan]Analyzing against[/cyan] {', '.join(framework_list)}..."
    )
    analyzer = GapAnalyzer()
    report = analyzer.analyze(
        inventory=inv,
        frameworks=framework_list,
        show_efficiency=show_efficiency_opportunities,
        min_efficiency_frameworks=min_efficiency_frameworks,
    )

    # Print summary
    table = Table(title="Gap Analysis Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="bold")
    table.add_row("Total controls required", str(report.total_controls_required))
    table.add_row("Total gaps", str(report.total_gaps))
    table.add_row("Critical", f"[red]{report.critical_gaps}[/red]")
    table.add_row("High", f"[orange1]{report.high_gaps}[/orange1]")
    table.add_row("Medium", f"[yellow]{report.medium_gaps}[/yellow]")
    table.add_row("Low", str(report.low_gaps))
    table.add_row("Coverage", f"{report.coverage_percentage}%")
    table.add_row("Efficiency opportunities", str(len(report.efficiency_opportunities)))
    console.print(table)

    # Top 5 priority gaps
    if report.gaps:
        top_table = Table(title="Top 5 Priority Gaps")
        top_table.add_column("#", style="dim")
        top_table.add_column("Framework", style="cyan")
        top_table.add_column("Control")
        top_table.add_column("Severity")
        top_table.add_column("Effort")
        top_table.add_column("Priority", justify="right", style="bold")
        for i, gap in enumerate(report.gaps[:5], 1):
            top_table.add_row(
                str(i),
                gap.framework,
                f"{gap.control_id} - {gap.control_title}",
                str(gap.gap_severity),
                str(gap.implementation_effort),
                f"{gap.priority_score:.2f}",
            )
        console.print(top_table)

    # Export
    out_path = export_report(report, output, format=format)  # type: ignore[arg-type]
    console.print(
        f"[green]Report exported:[/green] [bold]{out_path}[/bold] ({format})"
    )
