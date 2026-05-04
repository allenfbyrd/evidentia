"""`evidentia governance` — Governance commands (v0.7.10 P1.5).

Foundation for the v0.7.10 P1.5 governance primitives. Currently
ships:

  - ``evidentia governance lines-report --classifications <yaml>``

Future v0.7.10 sub-slices will extend this group with
``effective-challenge`` (P1.5 G2), KRI / KPI / KGI dashboards
(P1.5 G3+), Open FAIR risk quantification (P1.5 G4), and
process-as-code workflows (P1.5 G5).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import typer
import yaml
from evidentia_core.effective_challenge_store import (
    InvalidChallengeIdError,
    list_challenges,
    load_challenge_by_id,
    save_challenge,
)
from evidentia_core.governance import (
    ChallengeOutcome,
    EffectiveChallenge,
    LineOfDefense,
    Owner,
    generate_lines_report,
)
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Governance commands (3LOD + Effective Challenge).")
challenge_app = typer.Typer(help="Effective Challenge log commands.")
app.add_typer(challenge_app, name="challenge")

console = Console()


def _load_classifications(path: Path) -> list[Owner]:
    """Load a YAML overlay mapping email → line-of-defense classification.

    Expected YAML shape (one entry per owner)::

        - email: alice@example.com
          line_of_defense: first
          team: Loan Origination
          title: Senior Underwriter
        - email: bob@example.com
          line_of_defense: second
          team: MRM
          title: VP, Model Risk

    Returns the parsed list of :class:`Owner` instances. Exits
    cleanly with a clear error on parse failure.
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except OSError as e:
        console.print(f"[red]Error:[/red] could not read {path}: {e}")
        raise typer.Exit(code=1) from e
    except yaml.YAMLError as e:
        console.print(
            f"[red]Error:[/red] {path} is not valid YAML: {e}"
        )
        raise typer.Exit(code=1) from e

    if raw is None:
        # Empty file = no owners; let the report generator render
        # the empty-case narrative.
        return []
    if not isinstance(raw, list):
        console.print(
            f"[red]Error:[/red] {path} must be a YAML list of "
            "owner records (got "
            f"{type(raw).__name__})."
        )
        raise typer.Exit(code=1)

    owners: list[Owner] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            console.print(
                f"[red]Error:[/red] entry {i} in {path} is not a mapping; "
                f"got {type(entry).__name__}."
            )
            raise typer.Exit(code=1)
        try:
            owners.append(Owner.model_validate(entry))
        except ValidationError as e:
            console.print(
                f"[red]Error:[/red] entry {i} in {path} failed validation: {e}"
            )
            raise typer.Exit(code=1) from e
    return owners


@app.command("lines-report")
def lines_report(
    classifications: Path = typer.Option(
        ...,
        "--classifications",
        "-c",
        help=(
            "Path to a YAML overlay listing owners + line-of-defense "
            "classifications. See `evidentia governance lines-report "
            "--help` for the expected YAML shape."
        ),
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path. If omitted, prints to stdout.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite the output path if it already exists.",
    ),
) -> None:
    """Generate a Three Lines of Defense distribution report.

    Reads classified owners from a YAML overlay file and produces a
    Markdown distribution report covering:

      - Per-line counts + percentages
      - Crossover warning (any owner classified across multiple
        lines is flagged as a regulator-noted anti-pattern)
      - Per-line owner listing
      - Per-team breakdown showing which lines each team
        participates in

    The report is deterministic — same input produces the same
    output. Operators can therefore commit generated reports to git
    + audit-diff them across review cycles.
    """
    owners = _load_classifications(classifications)
    rendered = generate_lines_report(owners)

    if output is None:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
        return

    if output.exists() and not force:
        console.print(
            f"[red]Error:[/red] {output} already exists; pass --force to overwrite."
        )
        raise typer.Exit(code=1)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    n_first = sum(1 for o in owners if o.line_of_defense == LineOfDefense.FIRST.value)
    n_second = sum(1 for o in owners if o.line_of_defense == LineOfDefense.SECOND.value)
    n_third = sum(1 for o in owners if o.line_of_defense == LineOfDefense.THIRD.value)
    console.print(
        f"[green]Wrote[/green] 3LOD report to [bold]{output}[/bold] "
        f"({len(owners)} owner(s); 1st={n_first} / 2nd={n_second} / 3rd={n_third})."
    )


# ── effective challenge log (v0.7.10 P1.5 G2) ──────────────────────


def _parse_date_or_exit(value: str | None, flag: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        console.print(
            f"[red]Error:[/red] {flag} must be ISO-8601 date "
            f"(YYYY-MM-DD); got {value!r}: {e}"
        )
        raise typer.Exit(code=1) from e


@challenge_app.command("add")
def challenge_add(
    subject_model_id: str = typer.Option(
        ..., "--subject-model-id",
        help="ModelInventory.id being challenged.",
    ),
    challenger_email: str = typer.Option(
        ..., "--challenger-email",
        help="Email of the independent challenger.",
    ),
    challenger_role: str = typer.Option(
        ..., "--challenger-role",
        help="Challenger's role label (e.g., 'MRM Director').",
    ),
    challenge_date_str: str = typer.Option(
        ..., "--challenge-date",
        help="ISO-8601 date the challenge event occurred (YYYY-MM-DD).",
    ),
    challenge_topic: str = typer.Option(
        ..., "--challenge-topic",
        help="Short topic label.",
    ),
    challenge_substance: str = typer.Option(
        ..., "--challenge-substance",
        help="Full substantive challenge text.",
    ),
    response: str | None = typer.Option(
        None, "--response",
        help="Model owner's documented response (optional; can be added later via edit).",
    ),
    outcome: str = typer.Option(
        "pending", "--outcome",
        help="Outcome: accepted / rejected / modify / pending.",
    ),
    outcome_rationale: str | None = typer.Option(
        None, "--outcome-rationale",
        help="Rationale for the outcome decision.",
    ),
    resolved_at_str: str | None = typer.Option(
        None, "--resolved-at",
        help="ISO-8601 date the challenge was resolved.",
    ),
) -> None:
    """Add a new effective-challenge log record."""
    challenge_date_val = _parse_date_or_exit(challenge_date_str, "--challenge-date")
    resolved_at_val = _parse_date_or_exit(resolved_at_str, "--resolved-at")
    if challenge_date_val is None:
        # _parse_date_or_exit returns None only when value is None;
        # since challenge_date_str is required, this branch is
        # unreachable but typed for mypy.
        raise typer.Exit(code=1)
    try:
        outcome_enum = ChallengeOutcome(outcome)
    except ValueError as e:
        console.print(
            f"[red]Error:[/red] Unknown outcome {outcome!r}; valid: "
            f"{[o.value for o in ChallengeOutcome]}"
        )
        raise typer.Exit(code=1) from e

    try:
        challenge = EffectiveChallenge(
            subject_model_id=subject_model_id,
            challenger_email=challenger_email,
            challenger_role=challenger_role,
            challenge_date=challenge_date_val,
            challenge_topic=challenge_topic,
            challenge_substance=challenge_substance,
            response=response,
            outcome=outcome_enum,
            outcome_rationale=outcome_rationale,
            resolved_at=resolved_at_val,
        )
    except ValidationError as e:
        console.print(f"[red]Invalid challenge data:[/red] {e}")
        raise typer.Exit(code=1) from e

    save_challenge(challenge)
    console.print(
        f"[green]Logged[/green] challenge "
        f"[bold]{challenge.challenge_topic}[/bold] (id: {challenge.id})"
    )


@challenge_app.command("list")
def challenge_list(
    subject_model_id: str | None = typer.Option(
        None, "--subject-model-id",
        help="Filter by subject ModelInventory.id.",
    ),
    outcome: str | None = typer.Option(
        None, "--outcome",
        help="Filter by outcome: accepted / rejected / modify / pending.",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON array instead of a table.",
    ),
) -> None:
    """List challenge records sorted newest-first by challenge_date."""
    if outcome and outcome not in {o.value for o in ChallengeOutcome}:
        console.print(
            f"[red]Error:[/red] Unknown outcome {outcome!r}; valid: "
            f"{sorted(o.value for o in ChallengeOutcome)}"
        )
        raise typer.Exit(code=1)

    challenges = list_challenges()
    if subject_model_id:
        challenges = [c for c in challenges if c.subject_model_id == subject_model_id]
    if outcome:
        challenges = [c for c in challenges if c.outcome == outcome]

    if json_out:
        sys.stdout.write(
            json.dumps(
                [c.model_dump(mode="json") for c in challenges], indent=2
            )
        )
        sys.stdout.write("\n")
        return

    if not challenges:
        console.print(
            f"[dim]No challenges in the log "
            f"({len(list_challenges())} total without filter).[/dim]"
        )
        return

    table = Table(title=f"Effective Challenge log ({len(challenges)} matching)")
    table.add_column("ID", style="dim")
    table.add_column("Date")
    table.add_column("Topic", style="bold")
    table.add_column("Challenger")
    table.add_column("Role")
    table.add_column("Outcome", style="cyan")
    for c in challenges:
        table.add_row(
            c.id[:8],
            str(c.challenge_date),
            c.challenge_topic,
            c.challenger_email,
            c.challenger_role,
            c.outcome,
        )
    console.print(table)


@challenge_app.command("show")
def challenge_show(
    challenge_id: str = typer.Argument(..., help="Challenge ID (UUID)."),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON instead of formatted text.",
    ),
) -> None:
    """Show a single challenge record by ID."""
    try:
        challenge = load_challenge_by_id(challenge_id)
    except InvalidChallengeIdError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    if challenge is None:
        console.print(
            f"[red]Error:[/red] No challenge with ID {challenge_id!r} found."
        )
        raise typer.Exit(code=1)

    if json_out:
        sys.stdout.write(challenge.model_dump_json(indent=2))
        sys.stdout.write("\n")
        return

    console.print(f"[bold]{challenge.challenge_topic}[/bold]  [dim]({challenge.id})[/dim]")
    console.print(f"  Subject model:      {challenge.subject_model_id}")
    console.print(
        f"  Challenger:         {challenge.challenger_email} ({challenge.challenger_role})"
    )
    console.print(f"  Challenge date:     {challenge.challenge_date}")
    console.print(f"  Outcome:            [cyan]{challenge.outcome}[/cyan]")
    if challenge.resolved_at:
        console.print(f"  Resolved:           {challenge.resolved_at}")
    console.print(f"  Substance:          {challenge.challenge_substance}")
    if challenge.response:
        console.print(f"  Response:           {challenge.response}")
    if challenge.outcome_rationale:
        console.print(f"  Outcome rationale:  {challenge.outcome_rationale}")
    console.print(
        f"  [dim]Created: {challenge.created_at}  Updated: {challenge.updated_at}  "
        f"evidentia: {challenge.evidentia_version}[/dim]"
    )

