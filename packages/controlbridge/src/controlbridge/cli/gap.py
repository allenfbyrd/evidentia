"""`controlbridge gap` — gap analysis commands."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from controlbridge_core.gap_analyzer import GapAnalyzer, export_report, load_inventory
from controlbridge_core.models.gap import GapAnalysisReport
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
    from controlbridge_core.config import ControlBridgeConfig, get_default

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


# ---------------------------------------------------------------------------
# v0.3.0: `gap diff` — compare two gap snapshots (compliance-as-code)
# ---------------------------------------------------------------------------


@app.command("diff")
def diff(
    base: Path | None = typer.Option(
        None,
        "--base",
        "-b",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=(
            "Base gap report JSON (the 'before' state). "
            "If omitted with --head also omitted, auto-picks the two most "
            "recent reports from the gap store."
        ),
    ),
    head: Path | None = typer.Option(
        None,
        "--head",
        "-H",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Head gap report JSON (the 'after' state).",
    ),
    fail_on_regression: bool = typer.Option(
        False,
        "--fail-on-regression",
        help=(
            "Exit with code 1 if new gaps were opened or severities increased. "
            "Use this in CI to fail PR checks on compliance regressions."
        ),
    ),
    format: str = typer.Option(
        "console",
        "--format",
        help=(
            "Output format: console (Rich tables, default), json (machine-"
            "readable), markdown (PR-comment friendly), github (Actions "
            "workflow annotations)."
        ),
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write diff to this file instead of stdout.",
    ),
) -> None:
    """Compare two gap-analysis snapshots.

    Compares each ``(framework, control_id)`` pair across the two reports
    and classifies as one of: opened (new gap — regression), closed
    (gap fixed), severity_increased, severity_decreased, unchanged.

    Primary use: PR-level compliance checks. Pair with ``--fail-on-regression``
    in a GitHub Action to block PRs that make the compliance posture worse.
    See ``docs/github-action/`` for a full example workflow.
    """
    from controlbridge_core.gap_diff import (
        compute_gap_diff,
        render_github_annotations,
        render_markdown,
    )

    # Resolve base and head — explicit files > gap store auto-pick.
    if base is None or head is None:
        from controlbridge_core.gap_store import list_reports

        reports = list_reports()
        if len(reports) < 2:
            console.print(
                "[red]Error: need two gap reports to diff.[/red]\n"
                "[dim]Either pass --base and --head explicitly, or run "
                "`controlbridge gap analyze` twice so the gap store has "
                "something to compare.[/dim]"
            )
            raise typer.Exit(code=1)
        # Newest two — head is newest, base is second-newest
        if head is None:
            head = reports[0]
        if base is None:
            base = reports[1 if reports[0] == head else 0]
        console.print(
            f"[dim]Auto-picked from gap store — base: {base.name}, "
            f"head: {head.name}[/dim]"
        )

    base_report = GapAnalysisReport.model_validate_json(
        base.read_text(encoding="utf-8")
    )
    head_report = GapAnalysisReport.model_validate_json(
        head.read_text(encoding="utf-8")
    )

    diff_result = compute_gap_diff(base_report, head_report)

    # Render output. Non-console branches populate `text` (str); console
    # renders directly via Rich and leaves `text` unset.
    if format == "console":
        _render_diff_console(diff_result)
    elif format == "json":
        text = diff_result.model_dump_json(indent=2)
    elif format == "markdown":
        text = render_markdown(diff_result)
    elif format == "github":
        text = render_github_annotations(diff_result)
    else:
        console.print(f"[red]Unknown --format: {format!r}[/red]")
        raise typer.Exit(code=1)

    if format != "console":
        if output is not None:
            output.write_text(text, encoding="utf-8")
            console.print(f"[green]Diff written:[/green] {output}")
        else:
            # sys.stdout for json/markdown/github — bypass Rich so output
            # is byte-for-byte what downstream tooling expects.
            sys.stdout.write(text)
            sys.stdout.write("\n")

    # Exit code for CI gating
    if fail_on_regression and diff_result.summary.is_regression:
        console.print(
            f"\n[red]Compliance regression detected:[/red] "
            f"{diff_result.summary.opened} new gap(s), "
            f"{diff_result.summary.severity_increased} severity increase(s). "
            f"Exiting with code 1 (--fail-on-regression)."
        )
        raise typer.Exit(code=1)


def _render_diff_console(diff) -> None:  # type: ignore[no-untyped-def]
    """Rich-formatted tables for terminal use.

    Uses ASCII-only glyphs in the Rich output path so Windows legacy
    consoles (cp1252) don't raise UnicodeEncodeError. Emoji are reserved
    for the markdown renderer (PR comments) and the GitHub-annotation
    renderer, which target UTF-8-clean surfaces.
    """
    s = diff.summary
    title = (
        "[red]FAIL - Compliance regression[/red]"
        if s.is_regression
        else "[green]PASS - No regression[/green]"
    )
    header = Table(title=f"Gap Diff -- {title}")
    header.add_column("Status", style="cyan")
    header.add_column("Count", justify="right", style="bold")
    header.add_row("Opened (regressions)", f"[red]{s.opened}[/red]")
    header.add_row("Severity increased", f"[red]{s.severity_increased}[/red]")
    header.add_row("Severity decreased", f"[green]{s.severity_decreased}[/green]")
    header.add_row("Closed", f"[green]{s.closed}[/green]")
    header.add_row("Unchanged", str(s.unchanged))
    console.print(header)

    if diff.opened_entries:
        t = Table(title="Opened gaps")
        t.add_column("Framework", style="cyan")
        t.add_column("Control")
        t.add_column("Severity")
        for e in diff.opened_entries[:20]:
            t.add_row(
                e.framework,
                f"{e.control_id} - {e.control_title or ''}",
                str(e.head_severity),
            )
        console.print(t)

    if diff.severity_increased_entries:
        t = Table(title="Severity increased")
        t.add_column("Framework", style="cyan")
        t.add_column("Control")
        t.add_column("Base -> Head")
        for e in diff.severity_increased_entries[:20]:
            t.add_row(
                e.framework,
                f"{e.control_id} - {e.control_title or ''}",
                f"{e.base_severity} -> {e.head_severity}",
            )
        console.print(t)

    if diff.closed_entries:
        console.print(
            f"[green]{len(diff.closed_entries)} gap(s) closed[/green]"
        )
