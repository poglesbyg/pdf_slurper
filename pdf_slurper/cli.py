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
) -> None:
    init_db(db)
    result: SlurpResult = slurp_pdf(pdf_path, db_path=db)
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
) -> None:
    init_db(db)
    with open_session(db) as session:
        subs = db_list_submissions(session, limit=limit)
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
) -> None:
    init_db(db)
    with open_session(db) as session:
        sub = session.get(Submission, submission_id)
        if not sub:
            console.print(f"[red]Submission not found:[/red] {submission_id}")
            raise typer.Exit(code=1)
        samples = list(session.exec(select(Sample).where(Sample.submission_id == sub.id)))
        if fmt == "json":
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
    }.items() if v is not None}
    with open_session(db) as session:
        ok = db_update_sample(session, sample_id, **fields)
        if not ok:
            console.print(f"[red]Sample not found:[/red] {sample_id}")
            raise typer.Exit(code=1)
        console.print(f"[green]Updated[/green] {sample_id}")

if __name__ == "__main__":
    app()


