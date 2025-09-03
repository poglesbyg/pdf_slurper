"""API schemas for submissions."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SubmissionMetadataResponse(BaseModel):
    """Submission metadata response schema - enhanced with all fields."""
    
    # Basic identification
    identifier: Optional[str] = None
    
    # Service information
    service_requested: Optional[str] = None
    as_of: Optional[str] = None
    expires_on: Optional[str] = None
    request_summary: Optional[str] = None
    forms_text: Optional[str] = None
    
    # Contact information
    requester: Optional[str] = None
    requester_email: Optional[str] = None
    phone: Optional[str] = None
    lab: Optional[str] = None
    pis: Optional[str] = None
    financial_contacts: Optional[str] = None
    
    # Billing
    billing_address: Optional[str] = None
    
    # Sample information
    will_submit_dna_for: Optional[str] = None
    type_of_sample: Optional[str] = None
    human_dna: Optional[str] = None
    source_organism: Optional[str] = None
    sample_buffer: Optional[str] = None
    
    # Legacy compatibility
    organism: Optional[str] = None
    contains_human_dna: Optional[bool] = None
    
    # Storage and tracking
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionResponse(BaseModel):
    """Submission response schema."""
    
    id: str
    created_at: datetime
    updated_at: datetime
    sample_count: int
    metadata: SubmissionMetadataResponse
    pdf_source: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionListResponse(BaseModel):
    """Submission list response schema."""
    
    items: List[SubmissionResponse]
    total: int
    offset: int
    limit: int


class CreateSubmissionRequest(BaseModel):
    """Create submission request schema."""
    
    pdf_path: str = Field(..., description="Path to PDF file")
    force: bool = Field(False, description="Force re-import if exists")


class ApplyQCRequest(BaseModel):
    """Apply QC request schema."""
    
    min_concentration: float = Field(10.0, description="Minimum concentration (ng/µL)")
    min_volume: float = Field(20.0, description="Minimum volume (µL)")
    min_ratio: float = Field(1.8, description="Minimum A260/A280 ratio")
    evaluator: Optional[str] = Field(None, description="Person performing QC")


class QCResultResponse(BaseModel):
    """QC result response schema."""
    
    total: int
    passed: int
    warning: int
    failed: int
    skipped: int


class BatchUpdateStatusRequest(BaseModel):
    """Batch update status request schema."""
    
    sample_ids: List[str] = Field(..., description="Sample IDs to update")
    status: str = Field(..., description="New status")
    user: Optional[str] = Field(None, description="User performing update")


class SearchRequest(BaseModel):
    """Search request schema."""
    
    query: Optional[str] = Field(None, description="Search query")
    requester_email: Optional[str] = Field(None, description="Filter by requester email")
    lab: Optional[str] = Field(None, description="Filter by lab")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(0, ge=0, description="Results offset")


class UpdateSubmissionRequest(BaseModel):
    """Update submission request schema."""
    
    identifier: Optional[str] = Field(None, description="Identifier")
    service_requested: Optional[str] = Field(None, description="Service requested")
    requester: Optional[str] = Field(None, description="Requester name")
    requester_email: Optional[str] = Field(None, description="Requester email")
    lab: Optional[str] = Field(None, description="Laboratory")
    organism: Optional[str] = Field(None, description="Organism")
    storage_location: Optional[str] = Field(None, description="Storage location")


class SampleResponse(BaseModel):
    """Sample response schema."""
    
    id: str
    submission_id: str
    name: Optional[str] = None
    volume_ul: Optional[float] = None
    qubit_ng_per_ul: Optional[float] = None
    nanodrop_ng_per_ul: Optional[float] = None
    a260_a280: Optional[float] = None
    a260_a230: Optional[float] = None
    status: Optional[str] = Field(default="received")
    qc_status: Optional[str] = Field(default="pending")
    
    model_config = ConfigDict(from_attributes=True)


class UpdateSampleRequest(BaseModel):
    """Update sample request schema."""
    
    volume_ul: Optional[float] = None
    qubit_ng_per_ul: Optional[float] = None
    nanodrop_ng_per_ul: Optional[float] = None
    a260_a280: Optional[float] = None
    a260_a230: Optional[float] = None
    status: Optional[str] = None


class SampleListResponse(BaseModel):
    """Sample list response schema."""
    
    items: List[SampleResponse]
    total: int
    offset: int
    limit: int
