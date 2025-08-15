"""API schemas for submissions."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SubmissionMetadataResponse(BaseModel):
    """Submission metadata response schema."""
    
    identifier: Optional[str] = None
    service_requested: Optional[str] = None
    requester: Optional[str] = None
    requester_email: Optional[str] = None
    lab: Optional[str] = None
    organism: Optional[str] = None
    contains_human_dna: Optional[bool] = None
    
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


class StatisticsResponse(BaseModel):
    """Statistics response schema."""
    
    total_samples: int
    workflow_status: Dict[str, int]
    qc_status: Dict[str, int]
    average_concentration: Optional[float]
    average_volume: Optional[float]
    average_quality_score: Optional[float]
    samples_with_location: int
    samples_processed: int
