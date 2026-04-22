"""`controlbridge collect` — evidence-collection CLI commands.

v0.5.0 ships two collectors:

- ``collect aws`` — AWS Config + Security Hub findings
- ``collect github --repo owner/repo`` — branch protection + CODEOWNERS

Each command writes a list of :class:`SecurityFinding` objects as JSON
to ``--output`` (default: stdout) and prints a summary table.

Credentials:

- **AWS**: standard boto3 chain — env vars, ``~/.aws/credentials``,
  or instance profile.
- **GitHub**: ``GITHUB_TOKEN`` env var (personal access token or
  workflow token). Public repos also work unauthenticated, rate-limited.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

import typer
from controlbridge_core.models.finding import SecurityFinding
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    no_args_is_help=True,
    help="Evidence collectors — AWS, GitHub, etc.",
)

console = Console()


@app.command("aws")
def collect_aws(
    region: str | None = typer.Option(
        None,
        "--region",
        "-r",
        help="AWS region. Defaults to the SDK's resolved region.",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Optional AWS profile from ~/.aws/credentials.",
    ),
    include_config: bool = typer.Option(
        True,
        "--include-config/--no-config",
        help="Pull AWS Config non-compliant rule evaluations.",
    ),
    include_security_hub: bool = typer.Option(
        True,
        "--include-security-hub/--no-security-hub",
        help="Pull Security Hub active findings.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to write the findings JSON. Default: stdout.",
    ),
) -> None:
    """Collect evidence from AWS Config + Security Hub."""
    try:
        from controlbridge_collectors.aws import AwsCollector, AwsCollectorError
    except ImportError as e:
        console.print(
            "[red]Error:[/red] AWS collector is not installed. "
            "Run [cyan]pip install 'controlbridge-collectors[aws]'[/cyan]."
        )
        raise typer.Exit(code=1) from e

    try:
        collector = AwsCollector(region=region, profile=profile)
        identity = collector.test_connection()
    except AwsCollectorError as e:
        console.print(f"[red]AWS connection failed:[/red] {e}")
        raise typer.Exit(code=1) from e

    console.print(
        f"[dim]Collecting from account [bold]{identity['account']}[/bold] "
        f"in region [bold]{collector.region}[/bold]...[/dim]"
    )
    findings = collector.collect_all(
        include_config=include_config,
        include_security_hub=include_security_hub,
    )
    _write_findings(findings, output, title=f"AWS findings ({collector.region})")


@app.command("github")
def collect_github(
    repo: str = typer.Option(
        ...,
        "--repo",
        "-r",
        help="GitHub repository in 'owner/repo' format.",
    ),
    token: str | None = typer.Option(
        None,
        "--token",
        help=(
            "GitHub personal access token. Defaults to $GITHUB_TOKEN. "
            "Required for private repos and higher rate limits."
        ),
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to write the findings JSON. Default: stdout.",
    ),
) -> None:
    """Collect evidence from a GitHub repository."""
    try:
        from controlbridge_collectors.github import (
            GitHubApiError,
            GitHubCollector,
            GitHubCollectorError,
        )
    except ImportError as e:
        console.print(
            "[red]Error:[/red] GitHub collector failed to import: " + str(e)
        )
        raise typer.Exit(code=1) from e

    if "/" not in repo:
        console.print(
            "[red]Error:[/red] --repo must be 'owner/repo' format."
        )
        raise typer.Exit(code=1)
    owner, repo_name = repo.split("/", 1)

    resolved_token = token or os.environ.get("GITHUB_TOKEN")

    try:
        with GitHubCollector(
            owner=owner, repo=repo_name, token=resolved_token
        ) as collector:
            findings = collector.collect()
    except (GitHubCollectorError, GitHubApiError) as e:
        console.print(f"[red]GitHub collection failed:[/red] {e}")
        raise typer.Exit(code=1) from e

    _write_findings(findings, output, title=f"GitHub findings ({repo})")


# ── rendering ────────────────────────────────────────────────────────────


def _write_findings(
    findings: Iterable[SecurityFinding],
    output: Path | None,
    *,
    title: str,
) -> None:
    findings_list = list(findings)
    payload = [f.model_dump(mode="json") for f in findings_list]

    if output is not None:
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {len(findings_list)} findings to[/green] {output}")
    elif not findings_list:
        console.print("[yellow]No findings.[/yellow]")

    _render_summary(findings_list, title=title)


def _render_summary(findings: list[SecurityFinding], *, title: str) -> None:
    total = len(findings)
    by_severity: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for f in findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_source[f.source_system] = by_source.get(f.source_system, 0) + 1

    table = Table(title=f"{title} — {total} total")
    table.add_column("Severity", style="cyan")
    table.add_column("Count")
    for sev in ("critical", "high", "medium", "low", "informational"):
        if sev in by_severity:
            table.add_row(sev, str(by_severity[sev]))
    console.print(table)

    if by_source:
        src_table = Table(title="By source", show_header=True)
        src_table.add_column("Source")
        src_table.add_column("Count")
        for src, n in sorted(by_source.items()):
            src_table.add_row(src, str(n))
        console.print(src_table)
