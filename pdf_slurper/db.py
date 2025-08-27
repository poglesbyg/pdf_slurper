from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select


import os
DEFAULT_DB_PATH = Path(os.getenv("PDF_SLURPER_DB", str(Path.home() / ".pdf_slurper" / "db.sqlite3")))


def get_engine(db_path: Optional[Path] = None):
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=False)


class Submission(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_file: str
    source_sha256: str = Field(index=True)
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    page_count: int
    source_size: Optional[int] = Field(default=None, index=True)
    source_mtime: Optional[float] = Field(default=None, index=True)

    # Slurped metadata from PDF content
    identifier: Optional[str] = None
    as_of: Optional[str] = None
    expires_on: Optional[str] = None
    service_requested: Optional[str] = None
    requester: Optional[str] = None
    requester_email: Optional[str] = None
    phone: Optional[str] = None
    lab: Optional[str] = None
    billing_address: Optional[str] = None
    pis: Optional[str] = None
    financial_contacts: Optional[str] = None
    request_summary: Optional[str] = None
    forms_text: Optional[str] = None
    will_submit_dna_for_json: Optional[str] = None
    type_of_sample_json: Optional[str] = None
    human_dna: Optional[str] = None
    source_organism: Optional[str] = None
    sample_buffer_json: Optional[str] = None
    notes: Optional[str] = None  # Added for storing additional data like storage_location

    # Relationship omitted; fetch samples by filtering Sample.submission_id


class Sample(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    submission_id: str = Field(foreign_key="submission.id", index=True)
    row_index: int
    table_index: int
    page_index: int
    name: Optional[str] = None
    volume_ul: Optional[float] = None
    qubit_ng_per_ul: Optional[float] = None
    nanodrop_ng_per_ul: Optional[float] = None
    a260_a280: Optional[float] = None
    a260_a230: Optional[float] = None
    
    # Sample tracking fields
    status: Optional[str] = Field(default="received", index=True)  # received, processing, sequenced, completed, failed, on_hold
    location: Optional[str] = None  # e.g., "Freezer-A Shelf-3 Box-12 Position-A4"
    barcode: Optional[str] = Field(default=None, index=True)  # Sample barcode/ID
    processing_date: Optional[datetime] = None
    processed_by: Optional[str] = None  # Technician/user who processed
    
    # Quality control fields
    qc_status: Optional[str] = Field(default="pending")  # pending, passed, failed, warning
    qc_notes: Optional[str] = None
    concentration_threshold_passed: Optional[bool] = None
    volume_threshold_passed: Optional[bool] = None
    quality_score: Optional[float] = None  # 0-100 score
    
    # Additional tracking
    notes: Optional[str] = None  # General notes field for additional data
    sequencing_run_id: Optional[str] = None  # Link to sequencing run
    data_path: Optional[str] = None  # Path to result files
    repeat_of_sample_id: Optional[str] = None  # If this is a repeat/rerun
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to Submission omitted


def _column_exists_sqlite(engine, table: str, column: str) -> bool:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(f"PRAGMA table_info('{table}')").fetchall()
        return any(r[1] == column for r in rows)


def migrate_db(db_path: Optional[Path] = None) -> None:
    engine = get_engine(db_path)
    # Add source_sha256 if missing
    if not _column_exists_sqlite(engine, "submission", "source_sha256"):
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE submission ADD COLUMN source_sha256 VARCHAR")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_submission_source_sha256 ON submission (source_sha256)")
    # Add newly slurped metadata columns if missing
    submission_columns = [
        ("identifier", "TEXT"),
        ("as_of", "TEXT"),
        ("expires_on", "TEXT"),
        ("service_requested", "TEXT"),
        ("requester", "TEXT"),
        ("requester_email", "TEXT"),
        ("phone", "TEXT"),
        ("lab", "TEXT"),
        ("billing_address", "TEXT"),
        ("pis", "TEXT"),
        ("financial_contacts", "TEXT"),
        ("request_summary", "TEXT"),
        ("forms_text", "TEXT"),
        ("will_submit_dna_for_json", "TEXT"),
        ("type_of_sample_json", "TEXT"),
        ("human_dna", "TEXT"),
        ("source_organism", "TEXT"),
        ("sample_buffer_json", "TEXT"),
        ("source_size", "INTEGER"),
        ("source_mtime", "REAL"),
    ]
    for name, sqltype in submission_columns:
        if not _column_exists_sqlite(engine, "submission", name):
            with engine.begin() as conn:
                conn.exec_driver_sql(f"ALTER TABLE submission ADD COLUMN {name} {sqltype}")
    
    # Add new sample tracking columns if missing
    sample_columns = [
        ("status", "VARCHAR"),
        ("location", "TEXT"),
        ("barcode", "VARCHAR"),
        ("processing_date", "TIMESTAMP"),
        ("processed_by", "VARCHAR"),
        ("qc_status", "VARCHAR"),
        ("qc_notes", "TEXT"),
        ("concentration_threshold_passed", "BOOLEAN"),
        ("volume_threshold_passed", "BOOLEAN"),
        ("quality_score", "REAL"),
        ("notes", "TEXT"),
        ("sequencing_run_id", "VARCHAR"),
        ("data_path", "TEXT"),
        ("repeat_of_sample_id", "VARCHAR"),
        ("created_at", "TIMESTAMP"),
        ("updated_at", "TIMESTAMP"),
    ]
    for name, sqltype in sample_columns:
        if not _column_exists_sqlite(engine, "sample", name):
            with engine.begin() as conn:
                conn.exec_driver_sql(f"ALTER TABLE sample ADD COLUMN {name} {sqltype}")
    
    # Create indexes for frequently queried sample fields
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_sample_status ON sample (status)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_sample_barcode ON sample (barcode)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_sample_created_at ON sample (created_at)")


def init_db(db_path: Optional[Path] = None) -> Path:
    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)
    migrate_db(db_path)
    return Path(str(engine.url.database))


def open_session(db_path: Optional[Path] = None) -> Session:
    engine = get_engine(db_path)
    return Session(engine, expire_on_commit=False)


def get_submission(session: Session, submission_id: str) -> Optional[Submission]:
    return session.get(Submission, submission_id)


def find_submission_by_hash(session: Session, sha256: str) -> Optional[Submission]:
    stmt = select(Submission).where(Submission.source_sha256 == sha256)
    return session.exec(stmt).first()


def list_submissions(session: Session, limit: int = 50) -> list[Submission]:
    stmt = select(Submission).order_by(Submission.created_at.desc()).limit(limit)
    return list(session.exec(stmt))


def delete_submission(session: Session, submission_id: str) -> bool:
    obj = session.get(Submission, submission_id)
    if not obj:
        return False
    # delete samples first
    for s in session.exec(select(Sample).where(Sample.submission_id == submission_id)):
        session.delete(s)
    session.delete(obj)
    session.commit()
    return True


# Additional CRUD helpers
def create_sample(session: Session, sample: Sample) -> None:
    session.add(sample)
    session.commit()


def update_sample_fields(session: Session, sample_id: str, **fields) -> bool:
    obj = session.get(Sample, sample_id)
    if not obj:
        return False
    for k, v in fields.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    session.add(obj)
    session.commit()
    return True


def list_samples_for_submission(session: Session, submission_id: str, limit: int = 200) -> list[Sample]:
    stmt = select(Sample).where(Sample.submission_id == submission_id).limit(limit)
    return list(session.exec(stmt))


# New sample management functions
def batch_update_sample_status(session: Session, sample_ids: list[str], status: str, processed_by: Optional[str] = None) -> int:
    """Update status for multiple samples at once"""
    count = 0
    for sample_id in sample_ids:
        sample = session.get(Sample, sample_id)
        if sample:
            sample.status = status
            sample.updated_at = datetime.utcnow()
            if processed_by:
                sample.processed_by = processed_by
            if status in ["processing", "sequenced", "completed"]:
                sample.processing_date = datetime.utcnow()
            session.add(sample)
            count += 1
    session.commit()
    return count


def apply_qc_thresholds(session: Session, submission_id: str, 
                        min_concentration: float = 10.0, 
                        min_volume: float = 20.0,
                        min_quality_ratio: float = 1.8) -> int:
    """Apply QC thresholds and update QC status for all samples in submission"""
    samples = list_samples_for_submission(session, submission_id)
    flagged_count = 0
    
    for sample in samples:
        qc_issues = []
        
        # Check concentration
        if sample.qubit_ng_per_ul is not None:
            sample.concentration_threshold_passed = sample.qubit_ng_per_ul >= min_concentration
            if not sample.concentration_threshold_passed:
                qc_issues.append(f"Low concentration: {sample.qubit_ng_per_ul} ng/µL")
        
        # Check volume
        if sample.volume_ul is not None:
            sample.volume_threshold_passed = sample.volume_ul >= min_volume
            if not sample.volume_threshold_passed:
                qc_issues.append(f"Low volume: {sample.volume_ul} µL")
        
        # Check quality ratio
        quality_ok = True
        if sample.a260_a280 is not None and sample.a260_a280 < min_quality_ratio:
            quality_ok = False
            qc_issues.append(f"Poor A260/A280: {sample.a260_a280}")
        
        # Calculate quality score (0-100)
        score_components = []
        if sample.concentration_threshold_passed is not None:
            score_components.append(100 if sample.concentration_threshold_passed else 0)
        if sample.volume_threshold_passed is not None:
            score_components.append(100 if sample.volume_threshold_passed else 0)
        if sample.a260_a280 is not None:
            # Scale ratio to 0-100 (1.8-2.0 is ideal)
            ratio_score = min(100, max(0, (sample.a260_a280 - 1.5) / 0.5 * 100))
            score_components.append(ratio_score)
        
        if score_components:
            sample.quality_score = sum(score_components) / len(score_components)
        
        # Set overall QC status
        if qc_issues:
            sample.qc_status = "failed" if len(qc_issues) >= 2 else "warning"
            sample.qc_notes = "; ".join(qc_issues)
            flagged_count += 1
        else:
            sample.qc_status = "passed"
            sample.qc_notes = None
        
        sample.updated_at = datetime.utcnow()
        session.add(sample)
    
    session.commit()
    return flagged_count


def get_samples_by_status(session: Session, status: str, limit: int = 100) -> list[Sample]:
    """Get all samples with a specific status"""
    stmt = select(Sample).where(Sample.status == status).order_by(Sample.created_at.desc()).limit(limit)
    return list(session.exec(stmt))


def add_sample_note(session: Session, sample_id: str, note: str, append: bool = True) -> bool:
    """Add or update notes for a sample"""
    sample = session.get(Sample, sample_id)
    if not sample:
        return False
    
    if append and sample.notes:
        sample.notes = f"{sample.notes}\n[{datetime.utcnow().isoformat()}] {note}"
    else:
        sample.notes = f"[{datetime.utcnow().isoformat()}] {note}"
    
    sample.updated_at = datetime.utcnow()
    session.add(sample)
    session.commit()
    return True


def update_sample_location(session: Session, sample_id: str, location: str) -> bool:
    """Update storage location for a sample"""
    sample = session.get(Sample, sample_id)
    if not sample:
        return False
    
    sample.location = location
    sample.updated_at = datetime.utcnow()
    session.add(sample)
    session.commit()
    return True


def get_submission_statistics(session: Session, submission_id: str) -> dict:
    """Get statistics for a submission"""
    samples = list_samples_for_submission(session, submission_id)
    
    stats = {
        "total_samples": len(samples),
        "status_counts": {},
        "qc_status_counts": {},
        "average_concentration": 0,
        "average_volume": 0,
        "average_quality_score": 0,
        "samples_with_location": 0,
        "samples_processed": 0,
    }
    
    concentrations = []
    volumes = []
    quality_scores = []
    
    for sample in samples:
        # Status counts
        stats["status_counts"][sample.status or "unknown"] = stats["status_counts"].get(sample.status or "unknown", 0) + 1
        
        # QC status counts
        stats["qc_status_counts"][sample.qc_status or "pending"] = stats["qc_status_counts"].get(sample.qc_status or "pending", 0) + 1
        
        # Collect metrics
        if sample.qubit_ng_per_ul is not None:
            concentrations.append(sample.qubit_ng_per_ul)
        if sample.volume_ul is not None:
            volumes.append(sample.volume_ul)
        if sample.quality_score is not None:
            quality_scores.append(sample.quality_score)
        if sample.location:
            stats["samples_with_location"] += 1
        if sample.processing_date:
            stats["samples_processed"] += 1
    
    # Calculate averages
    if concentrations:
        stats["average_concentration"] = sum(concentrations) / len(concentrations)
    if volumes:
        stats["average_volume"] = sum(volumes) / len(volumes)
    if quality_scores:
        stats["average_quality_score"] = sum(quality_scores) / len(quality_scores)
    
    return stats


