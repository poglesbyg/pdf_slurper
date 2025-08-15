from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import fitz  # PyMuPDF
import pdfplumber
import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import select

from .db import DEFAULT_DB_PATH, Submission, Sample, init_db, open_session
from .db import list_samples_for_submission as db_list_samples, update_sample_fields as db_update_sample
from .slurp import SlurpResult, slurp_pdf
from .exporters import submission_to_json, samples_to_csv
from .db import list_submissions as db_list_submissions, delete_submission as db_delete_submission
from datetime import datetime
from typing import Optional
from sqlmodel import select, col


app = typer.Typer(add_completion=False, no_args_is_help=True, help="""
Extract information and text from PDF files.

Examples:
  pdf-slurp info path/to/file.pdf
  pdf-slurp text path/to/file.pdf --pages "1,3-5" --output -
"""
)


console = Console()


def parse_pages_spec(pages_spec: Optional[str], total_pages: int) -> List[int]:
    if not pages_spec:
        return list(range(total_pages))

    selected_pages: List[int] = []
    tokens = [t.strip() for t in pages_spec.split(",") if t.strip()]
    for token in tokens:
        if "-" in token:
            start_str, end_str = token.split("-", 1)
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise typer.BadParameter(f"Invalid page range: '{token}'")
            if start < 1 or end < 1 or start > end:
                raise typer.BadParameter(f"Invalid page range: '{token}'")
            for one_based in range(start, end + 1):
                if one_based <= total_pages:
                    selected_pages.append(one_based - 1)
        else:
            try:
                one_based = int(token)
            except ValueError:
                raise typer.BadParameter(f"Invalid page number: '{token}'")
            if one_based < 1 or one_based > total_pages:
                continue
            selected_pages.append(one_based - 1)

    # Deduplicate while preserving order
    seen = set()
    ordered_unique = []
    for p in selected_pages:
        if p not in seen:
            seen.add(p)
            ordered_unique.append(p)
    return ordered_unique


@app.command()
def info(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Input PDF file"),
) -> None:
    """Print basic metadata and page information."""
    with fitz.open(pdf_path) as document:
        metadata = document.metadata or {}

        table = Table(title="PDF Metadata", show_lines=False)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="white")

        table.add_row("Pages", str(document.page_count))
        for key in [
            "format",
            "encryption",
            "author",
            "title",
            "subject",
            "creator",
            "producer",
            "creationDate",
            "modDate",
            "keywords",
        ]:
            value = metadata.get(key)
            if value is not None:
                table.add_row(key, str(value))

        if document.page_count:
            first_page = document.load_page(0)
            mediabox = first_page.rect
            table.add_row("First page size (pt)", f"{mediabox.width:.2f} x {mediabox.height:.2f}")

        console.print(table)


@app.command()
def text(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Input PDF file"),
    pages: Optional[str] = typer.Option(None, help="Pages to extract, 1-based. Examples: '1', '2-5', '1,3-4'"),
    output: Path = typer.Option(Path("-"), help="Output file path or '-' for stdout"),
    page_separator: str = typer.Option("\n\n---\n\n", help="Separator inserted between pages"),
) -> None:
    """Extract text from pages and write to a file or stdout."""
    with fitz.open(pdf_path) as document:
        page_indices = parse_pages_spec(pages, document.page_count)
        chunks: List[str] = []
        for page_index in page_indices:
            page = document.load_page(page_index)
            chunks.append(page.get_text("text"))

    result_text = page_separator.join(chunks)

    if str(output) == "-":
        console.print(result_text)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result_text, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {len(result_text)} chars to {output}")


@app.command()
def tables(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Input PDF file"),
    pages: Optional[str] = typer.Option(None, help="Pages to parse for tables, 1-based"),
    output: Path = typer.Option(Path("-"), help="Output CSV path or '-' for stdout"),
) -> None:
    """Extract tables as CSV using pdfplumber."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        page_indices = parse_pages_spec(pages, total_pages)
        import csv
        import io

        rows: List[List[str]] = []
        for page_index in page_indices:
            page = pdf.pages[page_index]
            tables = page.extract_tables()
            for table in tables or []:
                for row in table:
                    if row is None:
                        continue
                    rows.append([(cell or "").strip() if isinstance(cell, str) else "" for cell in row])

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for row in rows:
            writer.writerow(row)
        csv_text = buffer.getvalue()

    if str(output) == "-":
        console.print(csv_text)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(csv_text, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {len(rows)} rows to {output}")


@app.command("db-init")
def db_init(
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    path = init_db(db)
    console.print(f"[green]Initialized DB at[/green] {path}")


@app.command("slurp")
def slurp(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
    force: bool = typer.Option(False, help="Force re-slurp even if file hash already exists"),
) -> None:
    init_db(db)
    result: SlurpResult = slurp_pdf(pdf_path, db_path=db, pages=None, force=force)
    console.print(f"[green]Created submission[/green] {result.submission_id} with {result.num_samples} samples")


@app.command("show-submission")
def show_submission(
    submission_id: str = typer.Argument(...),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
    limit: int = typer.Option(20, help="Limit number of samples displayed"),
) -> None:
    init_db(db)
    with open_session(db) as session:
        sub = session.get(Submission, submission_id)
        if not sub:
            console.print(f"[red]Submission not found:[/red] {submission_id}")
            raise typer.Exit(code=1)

        table = Table(title=f"Submission {sub.id}")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value")
        table.add_row("source_file", sub.source_file)
        table.add_row("title", str(sub.title))
        table.add_row("page_count", str(sub.page_count))
        table.add_row("created_at", str(sub.created_at))
        console.print(table)

        samples_table = Table(title="Samples")
        for col in ["id","row","table","page","name","vol(µL)","qubit","nanodrop","A260/280","A260/230"]:
            samples_table.add_column(col)

        count = 0
        for sample in session.exec(select(Sample).where(Sample.submission_id == sub.id)):
            samples_table.add_row(
                sample.id,
                str(sample.row_index),
                str(sample.table_index),
                str(sample.page_index + 1),
                sample.name or "",
                "" if sample.volume_ul is None else f"{sample.volume_ul}",
                "" if sample.qubit_ng_per_ul is None else f"{sample.qubit_ng_per_ul}",
                "" if sample.nanodrop_ng_per_ul is None else f"{sample.nanodrop_ng_per_ul}",
                "" if sample.a260_a280 is None else f"{sample.a260_a280}",
                "" if sample.a260_a230 is None else f"{sample.a260_a230}",
            )
            count += 1
            if count >= limit:
                break
        console.print(samples_table)


@app.command("list-submissions")
def list_submissions(
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
    limit: int = typer.Option(50, help="Max results"),
    since: Optional[str] = typer.Option(None, help="ISO date/time lower bound (e.g. 2025-08-14 or 2025-08-14T12:00:00)"),
    until: Optional[str] = typer.Option(None, help="ISO date/time upper bound"),
    title_contains: Optional[str] = typer.Option(None, help="Filter where title contains substring (case-insensitive)"),
    has_samples: bool = typer.Option(False, help="Only show submissions that have at least one sample"),
) -> None:
    init_db(db)
    with open_session(db) as session:
        # Build filtered query
        stmt = select(Submission)
        if since:
            try:
                dt = datetime.fromisoformat(since)
                stmt = stmt.where(Submission.created_at >= dt)
            except Exception:
                pass
        if until:
            try:
                dt = datetime.fromisoformat(until)
                stmt = stmt.where(Submission.created_at <= dt)
            except Exception:
                pass
        if title_contains:
            stmt = stmt.where((Submission.title.ilike(f"%{title_contains}%")))
        stmt = stmt.order_by(Submission.created_at.desc()).limit(limit)
        subs = list(session.exec(stmt))
        if has_samples:
            filtered = []
            for s in subs:
                cnt = session.exec(select(Sample).where(Sample.submission_id == s.id).limit(1)).first()
                if cnt is not None:
                    filtered.append(s)
            subs = filtered
        table = Table(title="Submissions")
        table.add_column("id")
        table.add_column("created_at")
        table.add_column("title")
        table.add_column("file")
        for s in subs:
            table.add_row(s.id, str(s.created_at), s.title or "", s.source_file)
        console.print(table)


@app.command("delete-submission")
def delete_submission(
    submission_id: str = typer.Argument(...),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    init_db(db)
    with open_session(db) as session:
        ok = db_delete_submission(session, submission_id)
        if not ok:
            console.print(f"[red]Submission not found:[/red] {submission_id}")
            raise typer.Exit(code=1)
        console.print(f"[green]Deleted[/green] {submission_id}")


@app.command("export")
def export_submission(
    submission_id: str = typer.Argument(...),
    fmt: str = typer.Option("json", help="json or csv"),
    output: Path = typer.Option(Path("-"), help="Output path or '-' for stdout"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
    ndjson: bool = typer.Option(False, help="When fmt=json, write newline-delimited JSON of samples"),
) -> None:
    init_db(db)
    with open_session(db) as session:
        sub = session.get(Submission, submission_id)
        if not sub:
            console.print(f"[red]Submission not found:[/red] {submission_id}")
            raise typer.Exit(code=1)
        samples = list(session.exec(select(Sample).where(Sample.submission_id == sub.id)))
        if fmt == "json":
            if ndjson:
                import json
                lines = [json.dumps({
                    "submission_id": sub.id,
                    "sample": {
                        "id": s.id,
                        "row_index": s.row_index,
                        "table_index": s.table_index,
                        "page_index": s.page_index,
                        "name": s.name,
                        "volume_ul": s.volume_ul,
                        "qubit_ng_per_ul": s.qubit_ng_per_ul,
                        "nanodrop_ng_per_ul": s.nanodrop_ng_per_ul,
                        "a260_a280": s.a260_a280,
                        "a260_a230": s.a260_a230,
                    }
                }) for s in samples]
                text = "\n".join(lines) + "\n"
            else:
                text = submission_to_json(sub, samples)
        elif fmt == "csv":
            text = samples_to_csv(samples)
        else:
            console.print("[red]Unknown format[/red]")
            raise typer.Exit(code=2)
        if str(output) == "-":
            console.print(text)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
            console.print(f"[green]Wrote[/green] {output}")


@app.command("list-samples")
def list_samples(
    submission_id: str = typer.Argument(...),
    limit: int = typer.Option(50, help="Max results"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    init_db(db)
    with open_session(db) as session:
        rows = db_list_samples(session, submission_id, limit)
        table = Table(title=f"Samples for {submission_id}")
        for col in ["id","row","table","page","name","vol(µL)","qubit","nanodrop","A260/280","A260/230"]:
            table.add_column(col)
        for s in rows:
            table.add_row(
                s.id,
                str(s.row_index),
                str(s.table_index),
                str(s.page_index + 1),
                s.name or "",
                "" if s.volume_ul is None else f"{s.volume_ul}",
                "" if s.qubit_ng_per_ul is None else f"{s.qubit_ng_per_ul}",
                "" if s.nanodrop_ng_per_ul is None else f"{s.nanodrop_ng_per_ul}",
                "" if s.a260_a280 is None else f"{s.a260_a280}",
                "" if s.a260_a230 is None else f"{s.a260_a230}",
            )
        console.print(table)


@app.command("update-sample")
def update_sample(
    sample_id: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None),
    volume_ul: Optional[float] = typer.Option(None),
    qubit_ng_per_ul: Optional[float] = typer.Option(None),
    nanodrop_ng_per_ul: Optional[float] = typer.Option(None),
    a260_a280: Optional[float] = typer.Option(None),
    a260_a230: Optional[float] = typer.Option(None),
    status: Optional[str] = typer.Option(None, help="Sample status: received, processing, sequenced, completed, failed"),
    location: Optional[str] = typer.Option(None, help="Storage location"),
    barcode: Optional[str] = typer.Option(None, help="Sample barcode"),
    notes: Optional[str] = typer.Option(None, help="Add notes to sample"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    init_db(db)
    fields = {k: v for k, v in {
        "name": name,
        "volume_ul": volume_ul,
        "qubit_ng_per_ul": qubit_ng_per_ul,
        "nanodrop_ng_per_ul": nanodrop_ng_per_ul,
        "a260_a280": a260_a280,
        "a260_a230": a260_a230,
        "status": status,
        "location": location,
        "barcode": barcode,
    }.items() if v is not None}
    
    with open_session(db) as session:
        # Update main fields
        if fields:
            ok = db_update_sample(session, sample_id, **fields)
            if not ok:
                console.print(f"[red]Sample not found:[/red] {sample_id}")
                raise typer.Exit(code=1)
        
        # Add notes if provided
        if notes:
            from .db import add_sample_note
            add_sample_note(session, sample_id, notes)
        
        console.print(f"[green]Updated[/green] {sample_id}")


@app.command("batch-update-status")
def batch_update_status(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    status: str = typer.Argument(..., help="New status: received, processing, sequenced, completed, failed"),
    sample_ids: Optional[str] = typer.Option(None, help="Comma-separated sample IDs (if not provided, updates all)"),
    processed_by: Optional[str] = typer.Option(None, help="Name of person processing"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    """Update status for multiple samples at once"""
    init_db(db)
    with open_session(db) as session:
        if sample_ids:
            ids = [s.strip() for s in sample_ids.split(",")]
        else:
            # Get all samples for the submission
            samples = db_list_samples(session, submission_id)
            ids = [s.id for s in samples]
        
        from .db import batch_update_sample_status
        count = batch_update_sample_status(session, ids, status, processed_by)
        console.print(f"[green]Updated {count} samples to status:[/green] {status}")


@app.command("apply-qc")
def apply_qc(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    min_concentration: float = typer.Option(10.0, help="Minimum concentration (ng/µL)"),
    min_volume: float = typer.Option(20.0, help="Minimum volume (µL)"),
    min_ratio: float = typer.Option(1.8, help="Minimum A260/A280 ratio"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    """Apply QC thresholds and flag samples"""
    init_db(db)
    with open_session(db) as session:
        from .db import apply_qc_thresholds
        flagged = apply_qc_thresholds(session, submission_id, min_concentration, min_volume, min_ratio)
        
        # Show results
        table = Table(title=f"QC Results for {submission_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        table.add_row("Minimum Concentration", f"{min_concentration} ng/µL")
        table.add_row("Minimum Volume", f"{min_volume} µL")
        table.add_row("Minimum A260/A280", f"{min_ratio}")
        table.add_row("Samples Flagged", str(flagged))
        console.print(table)


@app.command("submission-stats")
def submission_stats(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    """Show statistics for a submission"""
    init_db(db)
    with open_session(db) as session:
        from .db import get_submission_statistics
        stats = get_submission_statistics(session, submission_id)
        
        # Display statistics
        table = Table(title=f"Statistics for {submission_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        
        table.add_row("Total Samples", str(stats["total_samples"]))
        table.add_row("Average Concentration", f"{stats['average_concentration']:.2f} ng/µL" if stats['average_concentration'] else "N/A")
        table.add_row("Average Volume", f"{stats['average_volume']:.2f} µL" if stats['average_volume'] else "N/A")
        table.add_row("Average Quality Score", f"{stats['average_quality_score']:.1f}%" if stats['average_quality_score'] else "N/A")
        table.add_row("Samples with Location", f"{stats['samples_with_location']}/{stats['total_samples']}")
        table.add_row("Samples Processed", f"{stats['samples_processed']}/{stats['total_samples']}")
        console.print(table)
        
        # Status breakdown
        if stats["status_counts"]:
            status_table = Table(title="Sample Status Breakdown")
            status_table.add_column("Status")
            status_table.add_column("Count")
            for status, count in stats["status_counts"].items():
                status_table.add_row(status, str(count))
            console.print(status_table)
        
        # QC status breakdown
        if stats["qc_status_counts"]:
            qc_table = Table(title="QC Status Breakdown")
            qc_table.add_column("QC Status")
            qc_table.add_column("Count")
            for status, count in stats["qc_status_counts"].items():
                qc_table.add_row(status, str(count))
            console.print(qc_table)


@app.command("generate-manifest")
def generate_manifest(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    output: Path = typer.Option(Path("-"), help="Output CSV path or '-' for stdout"),
    include_qc: bool = typer.Option(True, help="Include QC information"),
    db: Path = typer.Option(DEFAULT_DB_PATH, help="SQLite DB path"),
) -> None:
    """Generate a sample manifest with all tracking information"""
    init_db(db)
    with open_session(db) as session:
        samples = db_list_samples(session, submission_id, limit=1000)
        
        import csv
        import io
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        # Header
        header = ["Sample_ID", "Name", "Barcode", "Status", "Location", 
                 "Volume_uL", "Conc_ng_uL", "A260_A280"]
        if include_qc:
            header.extend(["QC_Status", "Quality_Score", "QC_Notes"])
        writer.writerow(header)
        
        # Data rows
        for s in samples:
            row = [
                s.id,
                s.name or "",
                s.barcode or "",
                s.status or "received",
                s.location or "",
                s.volume_ul or "",
                s.qubit_ng_per_ul or s.nanodrop_ng_per_ul or "",
                s.a260_a280 or "",
            ]
            if include_qc:
                row.extend([
                    s.qc_status or "pending",
                    f"{s.quality_score:.1f}" if s.quality_score else "",
                    s.qc_notes or "",
                ])
            writer.writerow(row)
        
        csv_text = buffer.getvalue()
        
        if str(output) == "-":
            console.print(csv_text)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(csv_text, encoding="utf-8")
            console.print(f"[green]Wrote manifest to[/green] {output}")


if __name__ == "__main__":
    app()


