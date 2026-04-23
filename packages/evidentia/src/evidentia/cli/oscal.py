"""`evidentia oscal` — OSCAL integrity tooling (v0.7.0).

Today this namespace exposes one verb:

- ``evidentia oscal verify <path>`` — check SHA-256 digests of every
  embedded evidence resource in an OSCAL AR document, and optionally
  verify a detached GPG signature.

The evidence-embedding + signing side of the story lives under
``evidentia gap analyze --findings ... --sign-with-gpg <key-id>``.
Verification is separated so auditors who didn't produce the AR can
still run the check with just the JSON + ``.asc`` pair.
"""

from __future__ import annotations

from pathlib import Path

import typer
from evidentia_core.oscal.verify import DigestCheck, VerifyReport, verify_ar_file
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    no_args_is_help=True,
    help="OSCAL integrity + signature tooling.",
)
console = Console()


@app.command("verify")
def verify(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the OSCAL Assessment Results JSON file to verify.",
    ),
    require_signature: bool = typer.Option(
        False,
        "--require-signature",
        help=(
            "Fail verification if no detached GPG signature is found next "
            "to the AR file. Default behaviour is opportunistic — verify "
            "the sig if present, pass on digests alone if absent."
        ),
    ),
    signature: Path | None = typer.Option(
        None,
        "--signature",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=(
            "Custom signature file path. Defaults to <path>.asc next to "
            "the AR file."
        ),
    ),
    gnupghome: Path | None = typer.Option(
        None,
        "--gnupghome",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help=(
            "Override GNUPGHOME for signature verification. Useful when "
            "verifying against a specific keyring rather than the "
            "operator's default ~/.gnupg."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=(
            "Emit the verification report as machine-readable JSON to stdout. "
            "Exit code reflects overall pass/fail regardless of output mode."
        ),
    ),
) -> None:
    """Verify digests + optional GPG signature of an OSCAL AR document.

    Exits 0 on successful verification, 1 otherwise. Useful in CI
    pipelines that pull a signed AR from storage and need to fail the
    job if the chain of custody is broken.
    """
    report = verify_ar_file(
        path,
        require_signature=require_signature,
        signature_path=signature,
        gnupghome=gnupghome,
    )

    if json_output:
        _emit_json(report)
    else:
        _render_rich(report)

    raise typer.Exit(code=0 if report.overall_valid else 1)


def _render_rich(report: VerifyReport) -> None:
    """Human-readable summary of the verification outcome."""
    status_line = (
        "[green]PASS[/green]" if report.overall_valid else "[red]FAIL[/red]"
    )
    console.print(f"[bold]{report.ar_path}[/bold] — {status_line}")

    if report.errors:
        console.print("[red]Errors:[/red]")
        for err in report.errors:
            console.print(f"  - {err}")

    if report.digest_checks:
        _render_digest_table(report.digest_checks)
    else:
        console.print("[dim]No embedded evidence resources (digests skipped).[/dim]")

    if report.signature_valid is not None:
        sig_status = (
            "[green]valid[/green]" if report.signature_valid else "[red]INVALID[/red]"
        )
        console.print(f"Signature: {sig_status}")
        if report.signature_signer:
            console.print(
                f"  Signer key id: [cyan]{report.signature_signer}[/cyan]"
            )
        if report.signature_fingerprint:
            console.print(
                f"  Fingerprint:   [cyan]{report.signature_fingerprint}[/cyan]"
            )
    else:
        console.print("[dim]No signature checked.[/dim]")


def _render_digest_table(checks: list[DigestCheck]) -> None:
    """Tabulate per-resource digest outcomes."""
    total = len(checks)
    passed = sum(1 for c in checks if c.valid)
    table = Table(
        title=f"Evidence digests — {passed}/{total} valid",
        show_lines=False,
    )
    table.add_column("Status", style="bold")
    table.add_column("Resource UUID", style="dim")
    table.add_column("Title")
    for c in checks:
        marker = "[green]OK[/green]" if c.valid else "[red]FAIL[/red]"
        table.add_row(marker, c.resource_uuid[:8], c.title or "(untitled)")
    console.print(table)


def _emit_json(report: VerifyReport) -> None:
    """Serialize the VerifyReport as JSON for scripting / CI consumption."""

    payload = {
        "ar_path": str(report.ar_path),
        "overall_valid": report.overall_valid,
        "digests_valid": report.digests_valid,
        "signature_valid": report.signature_valid,
        "signature_signer": report.signature_signer,
        "signature_fingerprint": report.signature_fingerprint,
        "errors": report.errors,
        "digest_checks": [
            {
                "resource_uuid": c.resource_uuid,
                "title": c.title,
                "expected_digest": c.expected_digest,
                "actual_digest": c.actual_digest,
                "valid": c.valid,
            }
            for c in report.digest_checks
        ],
    }
    console.print_json(data=payload)
