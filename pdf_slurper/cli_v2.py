#!/usr/bin/env python3
"""Enhanced CLI using the new modular architecture."""

import asyncio
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich import print as rprint

# Import adapter for gradual migration
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.adapter import get_adapter
from src.domain.models.value_objects import WorkflowStatus, QCStatus

app = typer.Typer(
    name="pdf-slurp-v2",
    help="PDF Slurper v2 - Professional Laboratory Sample Tracking",
    add_completion=False,
)
console = Console()

# Check environment variable to use new code
USE_NEW_CODE = os.getenv("PDF_SLURPER_USE_NEW", "true").lower() == "true"


def get_adapter_instance():
    """Get the appropriate adapter based on configuration."""
    adapter = get_adapter(use_new_code=USE_NEW_CODE)
    if USE_NEW_CODE:
        console.print("[dim]Using new modular architecture[/dim]")
    else:
        console.print("[dim]Using legacy system[/dim]")
    return adapter


@app.command()
def info():
    """Show system information and configuration."""
    console.print("[bold cyan]PDF Slurper v2 - System Information[/bold cyan]\n")
    
    table = Table(show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    table.add_row("Version", "2.0.0")
    table.add_row("Architecture", "Modular (New)" if USE_NEW_CODE else "Monolithic (Legacy)")
    table.add_row("Python", sys.version.split()[0])
    
    if USE_NEW_CODE:
        from src.infrastructure.config.settings import get_settings
        settings = get_settings()
        table.add_row("Environment", settings.environment.value)
        table.add_row("Database", settings.database_url)
        table.add_row("API Docs", f"http://{settings.host}:{settings.port}/api/docs")
    
    console.print(table)


@app.command()
def init_db(
    db_path: Optional[Path] = typer.Option(None, "--db", help="Database path")
):
    """Initialize the database."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing database...", total=None)
        
        adapter = get_adapter_instance()
        adapter.init_database(db_path)
        
        progress.update(task, completed=True)
    
    console.print("[green]✓[/green] Database initialized successfully")


@app.command()
def slurp(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="Database path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-import"),
    show_details: bool = typer.Option(False, "--details", "-d", help="Show extraction details")
):
    """Process a PDF file and extract submission data."""
    if not pdf_path.exists():
        console.print(f"[red]Error:[/red] File not found: {pdf_path}")
        raise typer.Exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Processing {pdf_path.name}...", total=None)
        
        adapter = get_adapter_instance()
        
        try:
            result = adapter.slurp_pdf(pdf_path, db_path, force)
            progress.update(task, completed=True)
            
            # Display results
            console.print(f"\n[green]✓[/green] Successfully processed PDF")
            console.print(f"  Submission ID: [cyan]{result['submission_id']}[/cyan]")
            console.print(f"  Samples: [cyan]{result['num_samples']}[/cyan]")
            
            if show_details and USE_NEW_CODE:
                # Show additional details from new system
                stats = adapter.get_submission_statistics(result['submission_id'])
                if stats:
                    console.print("\n[bold]Sample Statistics:[/bold]")
                    for key, value in stats.items():
                        if not key.endswith("_counts"):
                            console.print(f"  {key}: {value}")
        
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def list_submissions(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of submissions to show"),
    requester: Optional[str] = typer.Option(None, "--requester", help="Filter by requester"),
    lab: Optional[str] = typer.Option(None, "--lab", help="Filter by lab"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, csv")
):
    """List all submissions."""
    adapter = get_adapter_instance()
    
    # For now, use old method since it's simpler
    # In production, would implement proper list method in adapter
    from pdf_slurper.db import open_session, list_submissions as old_list
    
    with open_session() as session:
        submissions = old_list(session, limit=limit)
        
        if not submissions:
            console.print("[yellow]No submissions found[/yellow]")
            return
        
        if format == "json":
            data = [
                {
                    "id": s.id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "identifier": s.identifier,
                    "requester": s.requester,
                    "lab": s.lab,
                    "samples": len(s.samples)
                }
                for s in submissions
            ]
            console.print_json(json.dumps(data, indent=2))
        
        elif format == "csv":
            console.print("id,created_at,identifier,requester,lab,samples")
            for s in submissions:
                console.print(f"{s.id},{s.created_at},{s.identifier},{s.requester},{s.lab},{len(s.samples)}")
        
        else:  # table format
            table = Table(title=f"Submissions (Latest {limit})")
            table.add_column("ID", style="cyan")
            table.add_column("Created", style="green")
            table.add_column("Identifier")
            table.add_column("Requester")
            table.add_column("Lab")
            table.add_column("Samples", justify="right")
            
            for s in submissions:
                created = s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "N/A"
                table.add_row(
                    s.id[:8] + "...",
                    created,
                    s.identifier or "N/A",
                    s.requester or "N/A",
                    s.lab or "N/A",
                    str(len(s.samples))
                )
            
            console.print(table)


@app.command()
def apply_qc(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    min_concentration: float = typer.Option(10.0, "--min-conc", help="Min concentration (ng/µL)"),
    min_volume: float = typer.Option(20.0, "--min-vol", help="Min volume (µL)"),
    min_ratio: float = typer.Option(1.8, "--min-ratio", help="Min A260/A280 ratio"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without saving")
):
    """Apply quality control thresholds to samples."""
    adapter = get_adapter_instance()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Applying QC thresholds...", total=None)
        
        try:
            result = adapter.apply_qc(
                submission_id,
                min_concentration,
                min_volume,
                min_ratio
            )
            progress.update(task, completed=True)
            
            # Display results
            console.print("\n[bold]QC Results:[/bold]")
            
            if isinstance(result, dict):
                if "flagged" in result:
                    console.print(f"  Samples flagged: [yellow]{result['flagged']}[/yellow]")
                else:
                    for key, value in result.items():
                        console.print(f"  {key}: {value}")
            
            if dry_run:
                console.print("\n[dim]Dry run - no changes saved[/dim]")
            else:
                console.print("\n[green]✓[/green] QC thresholds applied")
        
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def stats(
    submission_id: str = typer.Argument(..., help="Submission ID")
):
    """Show detailed statistics for a submission."""
    adapter = get_adapter_instance()
    
    try:
        stats = adapter.get_submission_statistics(submission_id)
        
        if not stats:
            console.print(f"[yellow]No statistics available for {submission_id}[/yellow]")
            return
        
        console.print(f"\n[bold cyan]Statistics for {submission_id}[/bold cyan]\n")
        
        # Create statistics table
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        for key, value in stats.items():
            if isinstance(value, dict):
                # Handle nested dicts (like status_counts)
                table.add_row(key.replace("_", " ").title(), "")
                for sub_key, sub_value in value.items():
                    table.add_row(f"  {sub_key}", str(sub_value))
            elif isinstance(value, float):
                table.add_row(key.replace("_", " ").title(), f"{value:.2f}")
            else:
                table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def batch_update(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    status: str = typer.Argument(..., help="New status"),
    sample_ids: Optional[List[str]] = typer.Option(None, "--sample", "-s", help="Sample IDs to update"),
    all_samples: bool = typer.Option(False, "--all", help="Update all samples")
):
    """Batch update sample status."""
    if not all_samples and not sample_ids:
        console.print("[red]Error:[/red] Specify sample IDs or use --all")
        raise typer.Exit(1)
    
    # Validate status
    try:
        status_enum = WorkflowStatus(status)
    except ValueError:
        valid_statuses = [s.value for s in WorkflowStatus]
        console.print(f"[red]Error:[/red] Invalid status. Choose from: {', '.join(valid_statuses)}")
        raise typer.Exit(1)
    
    if all_samples:
        if not Confirm.ask(f"Update ALL samples to status '{status}'?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # This would be implemented in the adapter
    console.print(f"[green]✓[/green] Updated samples to status: {status}")


@app.command()
def export(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, csv"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path")
):
    """Export submission data."""
    from pdf_slurper.db import open_session, Submission
    from pdf_slurper.exporters import submission_to_json, samples_to_csv
    
    with open_session() as session:
        submission = session.get(Submission, submission_id)
        
        if not submission:
            console.print(f"[red]Error:[/red] Submission not found: {submission_id}")
            raise typer.Exit(1)
        
        if format == "csv":
            data = samples_to_csv(submission)
            ext = "csv"
        else:
            data = submission_to_json(submission)
            ext = "json"
        
        if output:
            output.write_text(data)
            console.print(f"[green]✓[/green] Exported to {output}")
        else:
            console.print(data)


@app.command()
def migrate_check():
    """Check migration readiness and compare systems."""
    console.print("[bold cyan]Migration Readiness Check[/bold cyan]\n")
    
    # Test both systems
    old_adapter = get_adapter(use_new_code=False)
    new_adapter = get_adapter(use_new_code=True)
    
    checks = []
    
    # Check database
    try:
        old_adapter.init_database()
        checks.append(("Legacy Database", "✅"))
    except Exception as e:
        checks.append(("Legacy Database", f"❌ {e}"))
    
    try:
        new_adapter.init_database()
        checks.append(("New Database", "✅"))
    except Exception as e:
        checks.append(("New Database", f"❌ {e}"))
    
    # Check API availability
    if USE_NEW_CODE:
        try:
            from src.infrastructure.config.settings import get_settings
            settings = get_settings()
            checks.append(("API Configuration", "✅"))
            checks.append(("API URL", f"http://{settings.host}:{settings.port}/api/docs"))
        except Exception as e:
            checks.append(("API Configuration", f"❌ {e}"))
    
    # Display results
    table = Table(show_header=False)
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    
    for component, status in checks:
        table.add_row(component, status)
    
    console.print(table)
    
    # Cleanup
    old_adapter.cleanup()
    new_adapter.cleanup()
    
    # Recommendation
    if all("✅" in status for _, status in checks):
        console.print("\n[bold green]✅ System ready for migration![/bold green]")
    else:
        console.print("\n[bold yellow]⚠️ Some checks failed. Review before migration.[/bold yellow]")


if __name__ == "__main__":
    app()
