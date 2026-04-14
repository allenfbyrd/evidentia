"""`controlbridge catalog` — framework catalog exploration."""

from __future__ import annotations

import typer
from controlbridge_core.catalogs.registry import FRAMEWORK_METADATA, FrameworkRegistry
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Framework catalog exploration commands.")
console = Console()


@app.command("list")
def list_frameworks() -> None:
    """List all available framework catalogs."""
    registry = FrameworkRegistry.get_instance()

    table = Table(title="Available Framework Catalogs")
    table.add_column("Framework ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Controls", justify="right", style="green")
    table.add_column("Loaded", justify="center")

    for fw_id, meta in FRAMEWORK_METADATA.items():
        try:
            catalog = registry.get_catalog(fw_id)
            count = str(len(catalog.controls))
            loaded = "yes"
        except Exception:
            count = "-"
            loaded = "no"
        table.add_row(fw_id, meta.get("name", fw_id), count, loaded)

    console.print(table)


@app.command("show")
def show_catalog(
    framework: str = typer.Argument(..., help="Framework ID, e.g. 'nist-800-53-mod'."),
    control: str | None = typer.Option(
        None, "--control", "-c", help="Show detail for a specific control ID."
    ),
) -> None:
    """Show controls in a framework catalog (or detail for one control)."""
    registry = FrameworkRegistry.get_instance()
    try:
        catalog = registry.get_catalog(framework)
    except Exception as e:
        console.print(f"[red]Error loading catalog '{framework}': {e}[/red]")
        raise typer.Exit(code=1) from e

    if control:
        ctrl = catalog.get_control(control)
        if not ctrl:
            console.print(
                f"[red]Control '{control}' not found in '{framework}'.[/red]"
            )
            raise typer.Exit(code=1)

        body = (
            f"[bold]ID:[/bold] {ctrl.id}\n"
            f"[bold]Title:[/bold] {ctrl.title}\n"
            f"[bold]Family:[/bold] {ctrl.family or '-'}\n\n"
            f"[bold]Description:[/bold]\n{ctrl.description}\n"
        )
        if ctrl.enhancements:
            body += f"\n[bold]Enhancements:[/bold] {len(ctrl.enhancements)}\n"
            for enh in ctrl.enhancements[:10]:
                body += f"  * {enh.id}: {enh.title}\n"
        console.print(Panel(body, title=f"{framework} / {ctrl.id}", border_style="cyan"))
        return

    table = Table(title=f"{catalog.framework_name} ({catalog.framework_id})")
    table.add_column("Control ID", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Family", style="dim")

    for ctrl in catalog.controls:
        table.add_row(ctrl.id, ctrl.title, ctrl.family or "")

    console.print(table)
    console.print(f"[dim]Total: {len(catalog.controls)} controls[/dim]")


@app.command("crosswalk")
def show_crosswalk(
    source: str = typer.Option(..., "--source", "-s", help="Source framework ID."),
    target: str = typer.Option(..., "--target", "-t", help="Target framework ID."),
    control: str = typer.Option(..., "--control", "-c", help="Source control ID."),
) -> None:
    """Show cross-framework mappings for a control."""
    registry = FrameworkRegistry.get_instance()
    crosswalk = registry.crosswalk
    mappings = crosswalk.get_mapped_controls(source, control, target)

    if not mappings:
        console.print(
            f"[yellow]No mappings found from {source}:{control} to {target}.[/yellow]"
        )
        raise typer.Exit(code=0)

    console.print(
        f"[bold cyan]{source}[/bold cyan]:{control} maps to "
        f"[bold cyan]{target}[/bold cyan]:"
    )
    for m in mappings:
        title = m.target_control_title or ""
        rel = f"[dim]\\[{m.relationship}][/dim]"
        console.print(f"  -> [green]{m.target_control_id}[/green] {title} {rel}")
        if m.notes:
            console.print(f"     [dim]{m.notes}[/dim]")
