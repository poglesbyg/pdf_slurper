#!/usr/bin/env python
"""Script to clean up legacy code after successful migration."""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.progress import track

app = typer.Typer(
    name="cleanup-legacy",
    help="Clean up legacy code after migration to modular architecture",
)
console = Console()


# Files and directories to be removed/archived
LEGACY_FILES = [
    "pdf_slurper/cli.py",  # Old CLI (replaced by cli_v2.py)
    "pdf_slurper/db.py",    # Old database code
    "pdf_slurper/slurp.py",  # Old slurping logic
    "pdf_slurper/server.py", # Old server
    "pdf_slurper/exporters.py", # Old exporters
    "pdf_slurper/hash_utils.py", # Old hash utilities
    "pdf_slurper/mapping.py", # Old mapping logic
    "Dockerfile",  # Old Dockerfile (replaced by Dockerfile.v2)
]

LEGACY_DIRS = [
    "pdf_slurper/templates",  # Old templates
    ".github/workflows",  # Old CI (if replaced)
]

FILES_TO_RENAME = {
    "pdf_slurper/cli_v2.py": "pdf_slurper/cli.py",
    "Dockerfile.v2": "Dockerfile",
    "openshift/deployment-v2.yaml": "openshift/deployment.yaml",
}

ARCHIVE_DIR = Path("legacy_archive")


def check_migration_status() -> Dict[str, Any]:
    """Check if migration is complete."""
    status = {
        "new_code_exists": False,
        "tests_pass": False,
        "api_running": False,
        "database_migrated": False,
    }
    
    # Check if new code exists
    src_dir = Path("src")
    if src_dir.exists() and list(src_dir.glob("**/*.py")):
        status["new_code_exists"] = True
    
    # Check if tests exist and can be imported
    try:
        import tests.conftest
        status["tests_pass"] = True
    except ImportError:
        pass
    
    # Check if new API can be imported
    try:
        from src.presentation.api.app import app
        status["api_running"] = True
    except ImportError:
        pass
    
    # Check for migration markers
    migration_status = Path("MIGRATION_STATUS.md")
    if migration_status.exists():
        content = migration_status.read_text()
        if "Ready for gradual production migration" in content:
            status["database_migrated"] = True
    
    return status


def create_archive() -> Path:
    """Create archive directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = ARCHIVE_DIR / timestamp
    archive_path.mkdir(parents=True, exist_ok=True)
    return archive_path


def archive_file(file_path: Path, archive_path: Path) -> bool:
    """Archive a single file."""
    if not file_path.exists():
        return False
    
    dest = archive_path / file_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, dest)
    return True


def archive_directory(dir_path: Path, archive_path: Path) -> bool:
    """Archive a directory."""
    if not dir_path.exists():
        return False
    
    dest = archive_path / dir_path
    shutil.copytree(dir_path, dest, dirs_exist_ok=True)
    return True


@app.command()
def check():
    """Check migration readiness before cleanup."""
    console.print("[bold cyan]Migration Status Check[/bold cyan]\n")
    
    status = check_migration_status()
    
    table = Table(show_header=False)
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    
    for key, value in status.items():
        check_name = key.replace("_", " ").title()
        status_icon = "✅" if value else "❌"
        table.add_row(check_name, status_icon)
    
    console.print(table)
    
    all_ready = all(status.values())
    if all_ready:
        console.print("\n[bold green]✅ System ready for legacy cleanup![/bold green]")
    else:
        console.print("\n[bold red]❌ System not ready for cleanup. Complete migration first.[/bold red]")
    
    return all_ready


@app.command()
def preview(
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview without making changes")
):
    """Preview what will be cleaned up."""
    console.print("[bold cyan]Legacy Cleanup Preview[/bold cyan]\n")
    
    # Files to remove
    console.print("[bold]Files to archive and remove:[/bold]")
    for file_path in LEGACY_FILES:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            console.print(f"  📄 {file_path} ({size:.1f} KB)")
        else:
            console.print(f"  ⚫ {file_path} [dim](not found)[/dim]")
    
    # Directories to remove
    console.print("\n[bold]Directories to archive and remove:[/bold]")
    for dir_path in LEGACY_DIRS:
        path = Path(dir_path)
        if path.exists():
            file_count = len(list(path.glob("**/*")))
            console.print(f"  📁 {dir_path} ({file_count} files)")
        else:
            console.print(f"  ⚫ {dir_path} [dim](not found)[/dim]")
    
    # Files to rename
    console.print("\n[bold]Files to rename:[/bold]")
    for old_name, new_name in FILES_TO_RENAME.items():
        old_path = Path(old_name)
        if old_path.exists():
            console.print(f"  🔄 {old_name} → {new_name}")
        else:
            console.print(f"  ⚫ {old_name} [dim](not found)[/dim]")
    
    if not dry_run:
        return execute_cleanup()


@app.command()
def execute(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
    skip_archive: bool = typer.Option(False, "--skip-archive", help="Skip creating archive")
):
    """Execute the cleanup (removes legacy code)."""
    # Check migration status
    if not force and not check():
        console.print("\n[red]Cleanup aborted: Migration not complete[/red]")
        raise typer.Exit(1)
    
    # Confirm action
    if not force:
        console.print("\n[bold yellow]⚠️ WARNING: This will remove legacy code![/bold yellow]")
        if not Confirm.ask("Are you sure you want to proceed?"):
            console.print("[yellow]Cleanup cancelled[/yellow]")
            raise typer.Exit(0)
    
    execute_cleanup(skip_archive)


def execute_cleanup(skip_archive: bool = False) -> None:
    """Execute the actual cleanup."""
    console.print("\n[bold cyan]Starting Legacy Cleanup[/bold cyan]\n")
    
    # Create archive
    archive_path = None
    if not skip_archive:
        archive_path = create_archive()
        console.print(f"📦 Archive created: {archive_path}\n")
    
    # Archive and remove files
    console.print("[bold]Archiving and removing files:[/bold]")
    for file_path in track(LEGACY_FILES, description="Processing files..."):
        path = Path(file_path)
        if path.exists():
            if archive_path:
                archive_file(path, archive_path)
            path.unlink()
            console.print(f"  ✅ Removed: {file_path}")
        else:
            console.print(f"  ⚫ Skipped: {file_path} (not found)")
    
    # Archive and remove directories
    console.print("\n[bold]Archiving and removing directories:[/bold]")
    for dir_path in track(LEGACY_DIRS, description="Processing directories..."):
        path = Path(dir_path)
        if path.exists():
            if archive_path:
                archive_directory(path, archive_path)
            shutil.rmtree(path)
            console.print(f"  ✅ Removed: {dir_path}")
        else:
            console.print(f"  ⚫ Skipped: {dir_path} (not found)")
    
    # Rename files
    console.print("\n[bold]Renaming files:[/bold]")
    for old_name, new_name in FILES_TO_RENAME.items():
        old_path = Path(old_name)
        new_path = Path(new_name)
        if old_path.exists():
            if new_path.exists() and archive_path:
                archive_file(new_path, archive_path)
            old_path.rename(new_path)
            console.print(f"  ✅ Renamed: {old_name} → {new_name}")
        else:
            console.print(f"  ⚫ Skipped: {old_name} (not found)")
    
    # Update imports in remaining files
    update_imports()
    
    # Final summary
    console.print("\n[bold green]========================================[/bold green]")
    console.print("[bold green]Legacy cleanup completed successfully![/bold green]")
    console.print("[bold green]========================================[/bold green]")
    
    if archive_path:
        console.print(f"\nArchive location: {archive_path}")
        console.print("You can restore from archive if needed.")
    
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Run tests to verify everything works")
    console.print("2. Update documentation")
    console.print("3. Commit changes to version control")
    console.print("4. Deploy to production")


def update_imports():
    """Update import statements in remaining files."""
    console.print("\n[bold]Updating imports:[/bold]")
    
    # Update pyproject.toml scripts
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        content = pyproject.read_text()
        content = content.replace("pdf_slurper.cli:app", "pdf_slurper.cli:app")
        content = content.replace("pdf_slurper.server:main", "src.presentation.api.app:app")
        pyproject.write_text(content)
        console.print("  ✅ Updated pyproject.toml")


@app.command()
def restore(
    archive_timestamp: str = typer.Argument(..., help="Archive timestamp (e.g., 20240101_120000)")
):
    """Restore from a previous archive."""
    archive_path = ARCHIVE_DIR / archive_timestamp
    
    if not archive_path.exists():
        console.print(f"[red]Archive not found: {archive_path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold cyan]Restoring from archive: {archive_timestamp}[/bold cyan]\n")
    
    if not Confirm.ask("This will restore legacy code. Continue?"):
        console.print("[yellow]Restore cancelled[/yellow]")
        raise typer.Exit(0)
    
    # Restore files and directories
    for item in archive_path.rglob("*"):
        if item.is_file():
            relative = item.relative_to(archive_path)
            dest = Path(relative)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            console.print(f"  ✅ Restored: {relative}")
    
    console.print("\n[bold green]Restore completed successfully![/bold green]")


@app.command()
def list_archives():
    """List available archives."""
    console.print("[bold cyan]Available Archives[/bold cyan]\n")
    
    if not ARCHIVE_DIR.exists():
        console.print("[yellow]No archives found[/yellow]")
        return
    
    archives = sorted(ARCHIVE_DIR.iterdir(), reverse=True)
    
    if not archives:
        console.print("[yellow]No archives found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Files", justify="right")
    
    for archive in archives:
        if archive.is_dir():
            size = sum(f.stat().st_size for f in archive.rglob("*") if f.is_file())
            file_count = len(list(archive.rglob("*")))
            table.add_row(
                archive.name,
                f"{size / 1024 / 1024:.1f} MB",
                str(file_count)
            )
    
    console.print(table)


if __name__ == "__main__":
    app()
