"""`controlbridge integrations` — CLI wiring for output integrations.

v0.5.0 ships Jira only. ServiceNow / Vanta / Drata land in v0.5.1+.

Three subcommands under ``integrations jira``:

- ``test`` — validate creds + project access.
- ``push`` — push open gaps from a report as Jira issues.
- ``sync`` — pull status from Jira for every linked gap in a report.

All commands read credentials from environment variables (see
``docs/integrations/jira.md`` for the full list). ``--organization``,
``--project-key``, and friends are available as overrides for
scripting workflows.
"""

from __future__ import annotations

from pathlib import Path

import typer
from controlbridge_core.models.gap import GapAnalysisReport
from controlbridge_integrations.jira import (
    JiraApiError,
    JiraClient,
    JiraConfig,
    JiraSyncResult,
    push_open_gaps,
    sync_report,
)
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    no_args_is_help=True,
    help="Output integrations (Jira, ServiceNow, etc).",
)

jira_app = typer.Typer(
    no_args_is_help=True,
    help="Jira Cloud integration — push gaps as issues + status sync.",
)
app.add_typer(jira_app, name="jira")

console = Console()


def _load_report(gaps_path: Path) -> GapAnalysisReport:
    """Load a GapAnalysisReport from JSON on disk."""
    if not gaps_path.is_file():
        console.print(
            f"[red]Error:[/red] report not found: {gaps_path}. Run "
            "[cyan]controlbridge gap analyze[/cyan] first."
        )
        raise typer.Exit(code=1)
    return GapAnalysisReport.model_validate_json(
        gaps_path.read_text(encoding="utf-8")
    )


def _save_report(report: GapAnalysisReport, gaps_path: Path) -> None:
    """Persist an updated GapAnalysisReport back to the same path."""
    gaps_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _build_client() -> JiraClient:
    try:
        cfg = JiraConfig.from_env()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    return JiraClient(cfg)


@jira_app.command("test")
def jira_test() -> None:
    """Verify Jira credentials + project access.

    Exits 0 on success, 1 on any credential / API failure.
    """
    client = _build_client()
    try:
        info = client.test_connection()
    except JiraApiError as e:
        console.print(f"[red]Jira connection failed:[/red] {e}")
        raise typer.Exit(code=1) from e

    table = Table(title="Jira connection OK", show_lines=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for k in ("base_url", "user", "project_key", "project_name"):
        table.add_row(k, info.get(k, ""))
    console.print(table)


@jira_app.command("push")
def jira_push(
    gaps: Path = typer.Option(
        ...,
        "--gaps",
        "-g",
        help="Path to a GapAnalysisReport JSON (from `gap analyze --output`).",
    ),
    severity: str | None = typer.Option(
        None,
        "--severity",
        "-s",
        help=(
            "Comma-separated severities to push. E.g. 'critical,high'. "
            "Default: all severities."
        ),
    ),
    max_issues: int | None = typer.Option(
        None,
        "--max",
        help="Safety rail: cap total creates. Good for first-time runs.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Where to write the updated report. Default: overwrite the input. "
            "Pass '-' to skip the write (dry-run)."
        ),
    ),
) -> None:
    """Push open gaps from a report as Jira issues.

    Any gap whose ``jira_issue_key`` is already set is skipped. Severity
    filter restricts to only the severities listed. Exits 0 when all
    pushes succeed, 1 when any errored.
    """
    report = _load_report(gaps)

    severity_filter: set[str] | None = None
    if severity:
        severity_filter = {
            s.strip().lower() for s in severity.split(",") if s.strip()
        }

    with _build_client() as client:
        result = push_open_gaps(
            report,
            client,
            severity_filter=severity_filter,
            max_issues=max_issues,
        )

    _render_result(result, title="Jira push")

    if output is None:
        _save_report(report, gaps)
    elif str(output) != "-":
        _save_report(report, output)

    if result.errored > 0:
        raise typer.Exit(code=1)


@jira_app.command("sync")
def jira_sync(
    gaps: Path = typer.Option(
        ...,
        "--gaps",
        "-g",
        help="Path to a GapAnalysisReport JSON to sync.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to write the updated report. Default: overwrite the input.",
    ),
) -> None:
    """Pull status from Jira for every linked gap in the report."""
    report = _load_report(gaps)

    with _build_client() as client:
        result = sync_report(report, client)

    _render_result(result, title="Jira sync")

    if output is None:
        _save_report(report, gaps)
    elif str(output) != "-":
        _save_report(report, output)

    if result.errored > 0:
        raise typer.Exit(code=1)


def _render_result(result: JiraSyncResult, *, title: str) -> None:
    """Pretty-print a :class:`JiraSyncResult` as a Rich table."""
    table = Table(title=title, show_lines=False)
    table.add_column("Gap", style="cyan")
    table.add_column("Action")
    table.add_column("Issue")
    table.add_column("Detail")

    for o in result.outcomes:
        action_color = {
            "created": "green",
            "updated": "green",
            "skipped": "yellow",
            "errored": "red",
        }.get(o.action.value, "white")
        table.add_row(
            f"{o.framework}:{o.control_id}",
            f"[{action_color}]{o.action.value}[/{action_color}]",
            o.issue_key or "-",
            o.detail,
        )

    console.print(table)
    console.print(
        f"[bold]Summary:[/bold] created={result.created} "
        f"updated={result.updated} skipped={result.skipped} errored={result.errored}"
    )


@jira_app.command("status-map")
def jira_status_map(
    output_format: str = typer.Option(
        "table", "--format", "-f", help="Output format: 'table' or 'json'."
    ),
) -> None:
    """Print the Jira-status <-> GapStatus mapping currently in use."""
    from controlbridge_integrations.jira import (
        GAP_STATUS_TO_JIRA_STATUS,
        JIRA_STATUS_TO_GAP_STATUS,
    )

    if output_format == "json":
        console.print_json(
            data={
                "gap_status_to_jira": {
                    k.value: v for k, v in GAP_STATUS_TO_JIRA_STATUS.items()
                },
                "jira_status_to_gap": {
                    k: v.value for k, v in JIRA_STATUS_TO_GAP_STATUS.items()
                },
            }
        )
        return

    table = Table(title="GapStatus -> Jira (push)")
    table.add_column("GapStatus", style="cyan")
    table.add_column("Jira status name")
    for gs, jira_name in GAP_STATUS_TO_JIRA_STATUS.items():
        table.add_row(gs.value, jira_name)
    console.print(table)

    table2 = Table(title="Jira status -> GapStatus (sync)")
    table2.add_column("Jira status (case-insensitive)", style="cyan")
    table2.add_column("GapStatus")
    for jira_name, gs in JIRA_STATUS_TO_GAP_STATUS.items():
        table2.add_row(jira_name, gs.value)
    console.print(table2)
