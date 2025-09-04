"""SQLModel ORM models for database persistence."""

from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class SubmissionORM(SQLModel, table=True):
    """Submission ORM model."""
    
    __tablename__ = "submission_v2"  # Use different table name to avoid conflicts during migration
    
    # Primary key
    id: str = Field(primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # PDF source information
    source_file: str
    source_sha256: str = Field(index=True)
    source_size: Optional[int] = None
    source_mtime: Optional[float] = None
    page_count: int
    
    # PDF metadata
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    
    # Extracted metadata
    identifier: Optional[str] = Field(default=None, index=True)
    as_of: Optional[str] = None
    expires_on: Optional[str] = None
    service_requested: Optional[str] = None
    requester: Optional[str] = None
    requester_email: Optional[str] = Field(default=None, index=True)
    phone: Optional[str] = None
    lab: Optional[str] = Field(default=None, index=True)
    billing_address: Optional[str] = None
    storage_location: Optional[str] = None  # Storage location for samples
    pis: Optional[str] = None  # JSON string
    financial_contacts: Optional[str] = None  # JSON string
    request_summary: Optional[str] = None
    forms_text: Optional[str] = None
    will_submit_dna_for_json: Optional[str] = None
    type_of_sample_json: Optional[str] = None
    human_dna: Optional[str] = None
    source_organism: Optional[str] = None
    sample_buffer_json: Optional[str] = None
    # Additional comprehensive PDF extraction fields
    will_submit_dna_for: Optional[str] = Field(default=None)
    type_of_sample: Optional[str] = Field(default=None)
    sample_buffer: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=None)
    
    # Relationships
    samples: List["SampleORM"] = Relationship(
        back_populates="submission",
        cascade_delete=True
    )


class SampleORM(SQLModel, table=True):
    """Sample ORM model."""
    
    __tablename__ = "sample_v2"  # Use different table name to avoid conflicts during migration
    
    # Primary key
    id: str = Field(primary_key=True)
    
    # Foreign key
    submission_id: str = Field(foreign_key="submission_v2.id", index=True)
    
    # Position information
    row_index: int
    table_index: int
    page_index: int
    
    # Basic information
    name: Optional[str] = None
    
    # Measurements
    volume_ul: Optional[float] = None
    qubit_ng_per_ul: Optional[float] = None
    nanodrop_ng_per_ul: Optional[float] = None
    a260_a280: Optional[float] = None
    a260_a230: Optional[float] = None
    
    # Tracking fields
    status: Optional[str] = Field(default="received", index=True)
    location: Optional[str] = None
    barcode: Optional[str] = Field(default=None, index=True)
    processing_date: Optional[datetime] = None
    processed_by: Optional[str] = None
    
    # Quality control
    qc_status: Optional[str] = Field(default="pending", index=True)
    qc_notes: Optional[str] = None
    concentration_threshold_passed: Optional[bool] = None
    volume_threshold_passed: Optional[bool] = None
    quality_score: Optional[float] = None
    
    # Additional tracking
    notes: Optional[str] = None
    sequencing_run_id: Optional[str] = None
    data_path: Optional[str] = None
    repeat_of_sample_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    submission: Optional[SubmissionORM] = Relationship(back_populates="samples")
