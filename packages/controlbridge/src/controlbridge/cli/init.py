"""`controlbridge init` — bootstrap a new ControlBridge project."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


CONTROLBRIDGE_YAML = """\
# ControlBridge project configuration.
#
# v0.2.1: this file is now read by every `controlbridge` command (was
# decorative in v0.1.x/v0.2.0). Precedence for every setting:
#   CLI flag > CONTROLBRIDGE_* env var > this file > built-in default
#
# Supported keys as of v0.2.1 — everything else is accepted (for legacy
# compatibility) but ignored.

# Organization and system identity — overrides inventory-file values.
# Pairs with `gap analyze --organization` / `--system-name`.
organization: "Acme Corporation"
# system_name: "Acme Customer Portal"

# Default framework set for `gap analyze` when --frameworks is omitted.
# Populate with the canonical compliance scope for this project. CLI
# `--frameworks` replaces this list entirely (it does not union).
# Warning fires if this list has more than 5 frameworks.
frameworks:
{frameworks_yaml}

# LLM defaults for `risk generate`. Flag and
# CONTROLBRIDGE_LLM_MODEL / CONTROLBRIDGE_LLM_TEMPERATURE env vars win.
llm:
  model: "gpt-4o"
  temperature: 0.1

# ${{ENV_VAR}} interpolation is supported in any string value, e.g.:
#   organization: "${{ORG_NAME}}"
# so secrets and per-env settings can be hydrated from .env without
# committing them.
"""

MY_CONTROLS_YAML = """\
# Sample control inventory — replace with your organization's controls
organization: "Acme Corporation"
controls:
  - id: AC-2
    title: "Account Management"
    status: implemented
    implementation_notes: "Managed via Okta with quarterly access reviews."
    owner: "IAM Team"

  - id: AC-3
    title: "Access Enforcement"
    status: partially_implemented
    implementation_notes: "RBAC for production; permission model migration in progress."

  - id: AU-2
    title: "Audit Events"
    status: planned
    implementation_notes: "Centralized logging deployment scheduled for Q3."

  - id: IA-2
    title: "Identification and Authentication"
    status: implemented
    implementation_notes: "MFA enforced on all employee accounts via Okta."
"""

SYSTEM_CONTEXT_YAML = """\
# System context for AI risk statement generation
organization: "Acme Corporation"
system_name: "Acme Customer Portal"
system_description: |
  SaaS B2C platform serving customers across the United States.
  Processes account information, billing data, and support tickets.
data_classification:
  - PII
  - PCI-CDE
hosting: "AWS (us-east-1, us-west-2)"
risk_tolerance: "low"
regulatory_requirements:
  - PCI DSS
  - GDPR
  - CCPA
employee_count: 200
customer_count: 50000
threat_actors:
  - "External threat actors (financial)"
  - "Insider"
  - "Opportunistic ransomware groups"
existing_controls:
  - AC-2
  - IA-2
components:
  - name: "Web Application"
    type: web_app
    technology: "React + Node.js"
    data_handled: ["PII"]
    location: "AWS us-east-1"
  - name: "Payment Service"
    type: api
    technology: "Python + FastAPI"
    data_handled: ["PCI-CDE"]
    location: "AWS us-east-1 (PCI scope)"
  - name: "Customer Database"
    type: database
    technology: "Amazon RDS PostgreSQL"
    data_handled: ["PII", "PCI-CDE"]
"""


def init(
    directory: Path = typer.Option(
        Path("."),
        "--directory",
        "-d",
        help="Target directory for the new project (default: current directory).",
    ),
    frameworks: str = typer.Option(
        "nist-800-53-mod,soc2-tsc",
        "--frameworks",
        "-f",
        help="Comma-separated default framework IDs.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing files.",
    ),
) -> None:
    """Initialize a new ControlBridge project in the target directory."""
    directory.mkdir(parents=True, exist_ok=True)

    framework_list = [f.strip() for f in frameworks.split(",") if f.strip()]
    frameworks_yaml = "\n".join(f"    - {fw}" for fw in framework_list)

    files = {
        "controlbridge.yaml": CONTROLBRIDGE_YAML.format(frameworks_yaml=frameworks_yaml),
        "my-controls.yaml": MY_CONTROLS_YAML,
        "system-context.yaml": SYSTEM_CONTEXT_YAML,
    }

    created: list[str] = []
    skipped: list[str] = []

    for filename, content in files.items():
        target = directory / filename
        if target.exists() and not force:
            skipped.append(filename)
            continue
        target.write_text(content, encoding="utf-8")
        created.append(filename)

    storage = directory / ".controlbridge"
    storage.mkdir(exist_ok=True)

    console.print(f"[bold cyan]ControlBridge project initialized in[/bold cyan] {directory}")
    for f in created:
        console.print(f"  [green]created[/green]  {f}")
    for f in skipped:
        console.print(f"  [yellow]skipped[/yellow]  {f} (already exists; pass --force to overwrite)")
    console.print("  [green]created[/green]  .controlbridge/")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Edit [cyan]my-controls.yaml[/cyan] with your real control inventory.")
    console.print("  2. Run: [cyan]controlbridge gap analyze --inventory my-controls.yaml "
                  f"--frameworks {frameworks} --output report.json[/cyan]")
    console.print("  3. (Optional) Edit [cyan]system-context.yaml[/cyan] and run "
                  "[cyan]controlbridge risk generate ...[/cyan]")
