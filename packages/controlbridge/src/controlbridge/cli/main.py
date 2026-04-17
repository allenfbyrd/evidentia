"""ControlBridge CLI entry point.

The CLI is a thin Typer wrapper around the controlbridge_core, controlbridge_ai,
controlbridge_collectors, and controlbridge_integrations libraries.
"""

from __future__ import annotations

import logging
import sys

import typer
from rich.console import Console
from rich.table import Table

from controlbridge.cli import catalog as catalog_cmd
from controlbridge.cli import gap as gap_cmd
from controlbridge.cli import init as init_cmd
from controlbridge.cli import risk as risk_cmd

app = typer.Typer(
    name="controlbridge",
    help=(
        "ControlBridge: open-source GRC tool for gap analysis, risk statements, "
        "and compliance automation."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Sub-applications
app.add_typer(gap_cmd.app, name="gap", help="Gap analysis commands.")
app.add_typer(catalog_cmd.app, name="catalog", help="Framework catalog commands.")
app.add_typer(risk_cmd.app, name="risk", help="AI risk statement commands.")
app.command(name="init", help="Initialize a new ControlBridge project.")(init_cmd.init)

console = Console()


@app.callback()
def _global_options(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose (DEBUG) logging."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-error output."
    ),
    config: typer.FileText | None = typer.Option(
        None,
        "--config",
        help=(
            "Path to a controlbridge.yaml config file. Defaults to walking "
            "CWD \u2192 parents for the first `controlbridge.yaml` found."
        ),
    ),
) -> None:
    """Global options applied to all commands."""
    level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # v0.2.1: load controlbridge.yaml once and make it available to every
    # subcommand via ctx.obj. Subcommands consult it through
    # `controlbridge.config.get_default()` with the precedence rule
    # CLI flag > env var > yaml > built-in default.
    from pathlib import Path

    from controlbridge.config import load_config

    explicit_path = Path(config.name) if config is not None else None
    cfg = load_config(explicit_path)
    ctx.obj = {"config": cfg}
    if cfg.source_path is not None:
        logging.getLogger("controlbridge.config").debug(
            "Loaded config from %s", cfg.source_path
        )


@app.command()
def version() -> None:
    """Show ControlBridge version and Python environment information."""
    from controlbridge import __version__ as cb_version

    py = ".".join(str(v) for v in sys.version_info[:3])
    console.print(f"[bold cyan]ControlBridge[/bold cyan] v{cb_version}")
    console.print(f"Python {py}")


@app.command()
def doctor() -> None:
    """Run a diagnostic check of the ControlBridge installation."""
    from controlbridge_core.catalogs.registry import FrameworkRegistry

    table = Table(title="ControlBridge Diagnostics")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Detail")

    py = ".".join(str(v) for v in sys.version_info[:3])
    table.add_row("Python", "OK", py)

    # Core packages
    for pkg in [
        "controlbridge_core",
        "controlbridge_ai",
        "controlbridge_collectors",
        "controlbridge_integrations",
    ]:
        try:
            __import__(pkg)
            table.add_row(pkg, "OK", "installed")
        except ImportError as e:
            table.add_row(pkg, "MISSING", str(e))

    # Catalogs and crosswalks
    try:
        FrameworkRegistry.reset_instance()
        registry = FrameworkRegistry.get_instance()
        frameworks = registry.list_frameworks()
        table.add_row(
            "OSCAL catalogs",
            "OK",
            f"{len(frameworks)} frameworks registered",
        )

        crosswalk = registry.crosswalk
        table.add_row(
            "Crosswalks",
            "OK",
            f"{len(crosswalk.available_frameworks)} frameworks mapped",
        )
    except Exception as e:
        table.add_row("OSCAL catalogs", "FAIL", str(e))

    # LLM API key detection
    import os

    llm_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Anthropic",
        "GOOGLE_API_KEY": "Google",
        "AZURE_OPENAI_API_KEY": "Azure OpenAI",
    }
    detected = [name for env, name in llm_keys.items() if os.environ.get(env)]
    if detected:
        table.add_row("LLM provider", "OK", ", ".join(detected))
    else:
        table.add_row(
            "LLM provider",
            "WARN",
            "No API key detected (set OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)",
        )

    console.print(table)


if __name__ == "__main__":
    app()
