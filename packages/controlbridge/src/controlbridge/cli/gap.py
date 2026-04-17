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
    ctx: typer.Context,
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
    frameworks: str | None = typer.Option(
        None,
        "--frameworks",
        "-f",
        help=(
            "Comma-separated framework IDs, e.g. 'nist-800-53-mod,soc2-tsc'. "
            "Defaults to `frameworks:` list in controlbridge.yaml when omitted."
        ),
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
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-O",
        help=(
            "Override the organization name in the loaded inventory. "
            "Useful for CSV inputs (which have no org field) or when the "
            "inventory file's org name doesn't match the report recipient."
        ),
    ),
    system_name: str | None = typer.Option(
        None,
        "--system-name",
        help=(
            "Override the system / product name in the loaded inventory. "
            "Surfaces in report headers alongside the organization name."
        ),
    ),
) -> None:
    """Run gap analysis against one or more frameworks."""
    # v0.2.1: resolve inputs via the config-aware precedence chain:
    # CLI flag > controlbridge.yaml > required-or-error.
    from controlbridge.config import ControlBridgeConfig, get_default

    cfg_obj = ctx.obj.get("config") if ctx.obj else None
    cfg: ControlBridgeConfig = cfg_obj if cfg_obj is not None else ControlBridgeConfig()

    resolved_frameworks = get_default(cfg, frameworks, "frameworks", builtin_default=None)
    if not resolved_frameworks:
        console.print(
            "[red]Error: no frameworks specified.[/red] "
            "Pass --frameworks on the command line or add a `frameworks: [...]` "
            "list to your controlbridge.yaml."
        )
        raise typer.Exit(code=1)

    if isinstance(resolved_frameworks, str):
        framework_list = [f.strip() for f in resolved_frameworks.split(",") if f.strip()]
    else:
        framework_list = [f.strip() for f in resolved_frameworks if isinstance(f, str) and f.strip()]

    console.print(
        f"[cyan]Loading inventory from[/cyan] [bold]{inventory}[/bold]..."
    )
    inv = load_inventory(inventory)

    # v0.2.1: apply organization/system_name overrides via model_copy.
    # Precedence: CLI flag > yaml > inventory file > hardcoded default.
    resolved_org = get_default(cfg, organization, "organization", builtin_default=None)
    resolved_system = get_default(cfg, system_name, "system_name", builtin_default=None)
    overrides: dict[str, str] = {}
    if resolved_org:
        overrides["organization"] = resolved_org
    if resolved_system:
        overrides["system_name"] = resolved_system
    if overrides:
        inv = inv.model_copy(update=overrides)

    header = f"[bold]{inv.organization}[/bold]"
    if inv.system_name:
        header += f" / [bold]{inv.system_name}[/bold]"
    console.print(f"[green]Loaded[/green] {len(inv.controls)} controls for {header}")

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

    # v0.2.1: save a canonical copy to the user-dir gap store so
    # `controlbridge risk generate --gap-id GAP-…` can find the latest
    # report without the user re-specifying --gaps. Best-effort —
    # failures here shouldn't break the user's explicit --output export.
    try:
        from controlbridge_core.gap_store import save_report

        store_path = save_report(report)
        console.print(
            f"[dim]Gap store snapshot: {store_path} "
            f"(used by `risk generate --gap-id`)[/dim]"
        )
    except Exception as exc:
        console.print(
            f"[yellow]Note: could not write gap store snapshot: {exc}[/yellow]"
        )
