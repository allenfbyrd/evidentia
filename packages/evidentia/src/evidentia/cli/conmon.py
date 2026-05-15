"""`evidentia conmon` — Continuous Monitoring cycle-calendar commands.

v0.9.0 P3 read-only library surface. Operators consult the bundled
cadence catalog + compute next-due dates from a known anchor.

Subcommand structure:

    evidentia conmon list [--framework FW] [--json]
        # List all bundled (+ runtime-registered) cadences.

    evidentia conmon next <slug> --last-completed YYYY-MM-DD
        # Compute the next-due date for a specific cadence.

    evidentia conmon check --last-completed-file <path> [--today Y] [--window-days N] [--json]
        # Read a YAML mapping of {cadence_slug: last_completed_date}
        # and report due-soon + overdue cycles via derive_status.
        # Fires CONMON_CYCLE_DUE / CONMON_CYCLE_OVERDUE events for
        # each cycle that surfaces.

No daemon — operators poll. The CONMON live-trigger daemon
(``evidentia conmon watch``) is reserved for v1.0 per the
absolute-secrecy posture (out of v0.9.0 scope).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import typer
from evidentia_core.audit import EventAction, EventOutcome, get_logger
from evidentia_core.conmon import (
    CycleAttentionState,
    derive_status,
    get_cadence,
    list_cadences,
    next_due,
)
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Continuous Monitoring cycle calendar (v0.9.0 P3).")
console = Console()
_log = get_logger("evidentia.cli.conmon")


# ── helpers ────────────────────────────────────────────────────────


def _parse_date_or_exit(value: str | None, flag: str) -> date | None:
    """Parse an ISO-8601 date or exit cleanly. Mirrors cli/poam.py."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        console.print(
            f"[red]Error:[/red] {flag} must be ISO-8601 date "
            f"(YYYY-MM-DD); got {value!r}: {exc}"
        )
        raise typer.Exit(code=1) from exc


def _load_last_completed_map(
    path: Path,
) -> dict[str, date]:
    """Load a YAML mapping of {cadence_slug: last_completed_date}.

    Schema (YAML):

        nist-800-53-rev5-ca7: 2026-04-01
        fedramp-conmon-poam: 2026-04-15

    Raises :class:`typer.Exit` (code 1) on parse failure or invalid
    schema. Unknown slugs surface a warning at use time, not at
    parse time, so operators can keep entries for cadences they
    haven't yet rolled out.
    """
    import yaml as yaml_mod  # lazy import — keeps the CLI lean

    try:
        raw = yaml_mod.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml_mod.YAMLError as exc:
        console.print(f"[red]Error:[/red] could not parse {path}: {exc}")
        raise typer.Exit(code=1) from exc

    if not isinstance(raw, dict):
        console.print(
            f"[red]Error:[/red] {path} must be a YAML mapping of "
            f"slug → ISO-8601 date; got {type(raw).__name__}"
        )
        raise typer.Exit(code=1)

    out: dict[str, date] = {}
    for slug, value in raw.items():
        if not isinstance(slug, str):
            console.print(
                f"[red]Error:[/red] cadence keys must be strings; "
                f"got {slug!r}"
            )
            raise typer.Exit(code=1)
        if isinstance(value, date):
            out[slug] = value
        elif isinstance(value, str):
            try:
                out[slug] = date.fromisoformat(value)
            except ValueError as exc:
                console.print(
                    f"[red]Error:[/red] {slug!r} → {value!r}: "
                    f"expected ISO-8601 date ({exc})"
                )
                raise typer.Exit(code=1) from exc
        else:
            console.print(
                f"[red]Error:[/red] {slug!r} → {value!r}: expected "
                f"ISO-8601 date string"
            )
            raise typer.Exit(code=1)
    return out


# ── list ───────────────────────────────────────────────────────────


@app.command("list")
def conmon_list(
    framework: str | None = typer.Option(
        None,
        "--framework",
        "-f",
        help=(
            "Filter to cadences for a specific framework "
            "(e.g., nist-800-53-rev5, fedramp-rev5-mod, cmmc-v2)."
        ),
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON instead of a rich table.",
    ),
) -> None:
    """List bundled + registered CONMON cadences."""
    cadences = list_cadences(framework=framework)

    if output_json:
        typer.echo(
            json.dumps(
                [json.loads(c.model_dump_json()) for c in cadences],
                indent=2,
            )
        )
        return

    table = Table(title=f"CONMON cadences ({len(cadences)} total)")
    table.add_column("Slug", style="bold")
    table.add_column("Framework")
    table.add_column("Activity")
    table.add_column("Frequency", style="cyan")
    table.add_column("Citation")
    for cadence in cadences:
        table.add_row(
            cadence.slug,
            cadence.framework,
            cadence.activity,
            cadence.frequency,
            cadence.citation or "[dim]—[/dim]",
        )
    console.print(table)


# ── next ───────────────────────────────────────────────────────────


@app.command("next")
def conmon_next(
    slug: str = typer.Argument(..., help="Cadence slug."),
    last_completed: str = typer.Option(
        ...,
        "--last-completed",
        help="ISO-8601 date of the last completed cycle.",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON instead of human form.",
    ),
) -> None:
    """Compute the next-due date for a registered cadence."""
    cadence = get_cadence(slug)
    if cadence is None:
        console.print(
            f"[red]Error:[/red] unknown cadence slug {slug!r}. "
            f"Run `evidentia conmon list` to see available."
        )
        raise typer.Exit(code=1)

    anchor = _parse_date_or_exit(last_completed, "--last-completed")
    assert anchor is not None  # required by Typer (...)

    due = next_due(slug, anchor)

    if output_json:
        typer.echo(
            json.dumps(
                {
                    "slug": cadence.slug,
                    "framework": cadence.framework,
                    "activity": cadence.activity,
                    "frequency": cadence.frequency,
                    "last_completed": anchor.isoformat(),
                    "next_due": due.isoformat(),
                },
                indent=2,
            )
        )
        return

    console.print(
        f"[bold]{cadence.slug}[/bold] ({cadence.frequency})"
    )
    console.print(f"  Framework:       {cadence.framework}")
    console.print(f"  Activity:        {cadence.activity}")
    console.print(f"  Last completed:  {anchor.isoformat()}")
    console.print(
        f"  Next due:        [cyan]{due.isoformat()}[/cyan]"
    )
    if cadence.citation:
        console.print(f"  Citation:        [dim]{cadence.citation}[/dim]")


# ── check ──────────────────────────────────────────────────────────


@app.command("check")
def conmon_check(
    last_completed_file: Path = typer.Option(
        ...,
        "--last-completed-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=(
            "YAML mapping {cadence_slug: ISO-8601-date} of last-"
            "completed dates per cycle. Unknown slugs are warned "
            "(not errored)."
        ),
    ),
    today_override: str | None = typer.Option(
        None,
        "--today",
        help=(
            "Override 'today' for deterministic CLI snapshots "
            "(YYYY-MM-DD). Production operators omit this flag."
        ),
    ),
    window_days: int = typer.Option(
        14,
        "--window-days",
        min=0,
        help=(
            "Due-soon window (days from today). Default: 14 days. "
            "Overdue cycles always surface regardless of this window."
        ),
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON instead of human-readable tables.",
    ),
) -> None:
    """Report due-soon + overdue cycles from a tracked-state YAML.

    Fires :attr:`EventAction.CONMON_CYCLE_DUE` per due-soon cycle
    and :attr:`EventAction.CONMON_CYCLE_OVERDUE` per overdue cycle.
    Pure-current cycles (next_due_date > today + window_days) do
    NOT emit audit events — the absence of events is itself an
    auditor signal (no attention needed).
    """
    today_parsed = _parse_date_or_exit(today_override, "--today")
    today: date = today_parsed if today_parsed is not None else date.today()

    last_completed_map = _load_last_completed_map(last_completed_file)

    overdue: list[dict[str, str]] = []
    due_soon: list[dict[str, str]] = []
    unknown: list[str] = []

    for slug, anchor in last_completed_map.items():
        cadence = get_cadence(slug)
        if cadence is None:
            unknown.append(slug)
            continue
        due = next_due(slug, anchor)
        state = derive_status(due, today, window_days=window_days)
        days_until_due = (due - today).days
        row = {
            "slug": slug,
            "framework": cadence.framework,
            "activity": cadence.activity,
            "frequency": cadence.frequency,
            "last_completed": anchor.isoformat(),
            "next_due": due.isoformat(),
            "days_until_due": str(days_until_due),
        }
        if state == CycleAttentionState.OVERDUE:
            overdue.append(row)
            _log.warning(
                action=EventAction.CONMON_CYCLE_OVERDUE,
                outcome=EventOutcome.FAILURE,
                message=(
                    f"CONMON cycle {slug!r} is overdue "
                    f"({days_until_due} days past next-due)"
                ),
                evidentia={
                    "cadence_slug": slug,
                    "framework": cadence.framework,
                    "activity": cadence.activity,
                    "last_completed": anchor.isoformat(),
                    "next_due": due.isoformat(),
                    "days_until_due": days_until_due,
                },
            )
        elif state == CycleAttentionState.DUE_SOON:
            due_soon.append(row)
            _log.info(
                action=EventAction.CONMON_CYCLE_DUE,
                outcome=EventOutcome.SUCCESS,
                message=(
                    f"CONMON cycle {slug!r} due within "
                    f"{window_days} day(s) (next-due {due.isoformat()})"
                ),
                evidentia={
                    "cadence_slug": slug,
                    "framework": cadence.framework,
                    "activity": cadence.activity,
                    "last_completed": anchor.isoformat(),
                    "next_due": due.isoformat(),
                    "days_until_due": days_until_due,
                },
            )

    if output_json:
        typer.echo(
            json.dumps(
                {
                    "today": today.isoformat(),
                    "window_days": window_days,
                    "overdue": overdue,
                    "due_soon": due_soon,
                    "unknown_slugs": unknown,
                },
                indent=2,
            )
        )
        return

    if unknown:
        console.print(
            f"[yellow]Warning:[/yellow] {len(unknown)} unknown "
            f"cadence slug(s) in the file: {', '.join(unknown)}"
        )

    if not overdue and not due_soon:
        console.print(
            f"[green]No CONMON cycles overdue or due within "
            f"{window_days} day(s)[/green] as of {today.isoformat()}."
        )
        return

    if overdue:
        table = Table(
            title=(
                f"OVERDUE cycles ({len(overdue)}) as of {today.isoformat()}"
            ),
            title_style="bold red",
        )
        table.add_column("Slug", style="bold")
        table.add_column("Framework")
        table.add_column("Activity")
        table.add_column("Next due", style="red")
        table.add_column("Days past", justify="right", style="red")
        for row in overdue:
            table.add_row(
                row["slug"],
                row["framework"],
                row["activity"],
                row["next_due"],
                row["days_until_due"],
            )
        console.print(table)

    if due_soon:
        table = Table(
            title=(
                f"Due within {window_days} day(s) ({len(due_soon)}) "
                f"as of {today.isoformat()}"
            ),
            title_style="bold yellow",
        )
        table.add_column("Slug", style="bold")
        table.add_column("Framework")
        table.add_column("Activity")
        table.add_column("Next due", style="yellow")
        table.add_column("Days ahead", justify="right")
        for row in due_soon:
            table.add_row(
                row["slug"],
                row["framework"],
                row["activity"],
                row["next_due"],
                row["days_until_due"],
            )
        console.print(table)
