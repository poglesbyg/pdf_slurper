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
    columns = [
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
    ]
    for name, sqltype in columns:
        if not _column_exists_sqlite(engine, "submission", name):
            with engine.begin() as conn:
                conn.exec_driver_sql(f"ALTER TABLE submission ADD COLUMN {name} {sqltype}")


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


