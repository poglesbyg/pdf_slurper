"""Sample domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from .value_objects import (
    SampleId, WorkflowStatus, QCStatus, Concentration, Volume,
    QualityRatio, StorageLocation, Barcode, QualityScore
)


@dataclass
class Measurements:
    """Sample measurements."""
    volume: Optional[Volume] = None
    qubit_concentration: Optional[Concentration] = None
    nanodrop_concentration: Optional[Concentration] = None
    a260_a280: Optional[QualityRatio] = None
    a260_a230: Optional[QualityRatio] = None
    
    @property
    def best_concentration(self) -> Optional[Concentration]:
        """Get the most reliable concentration measurement."""
        # Prefer Qubit over Nanodrop for accuracy
        return self.qubit_concentration or self.nanodrop_concentration


@dataclass
class QCResult:
    """Quality control result."""
    status: QCStatus
    score: Optional[QualityScore] = None
    issues: List[str] = field(default_factory=list)
    passed_concentration: bool = False
    passed_volume: bool = False
    passed_quality_ratio: bool = False
    evaluated_at: Optional[datetime] = None
    evaluated_by: Optional[str] = None
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any QC issues."""
        return len(self.issues) > 0


@dataclass
class ProcessingInfo:
    """Sample processing information."""
    status: WorkflowStatus = WorkflowStatus.RECEIVED
    location: Optional[StorageLocation] = None
    barcode: Optional[Barcode] = None
    processed_by: Optional[str] = None
    processing_date: Optional[datetime] = None
    sequencing_run_id: Optional[str] = None
    data_path: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    
    def add_note(self, note: str, author: Optional[str] = None) -> None:
        """Add a timestamped note."""
        timestamp = datetime.utcnow().isoformat()
        if author:
            self.notes.append(f"[{timestamp}] {author}: {note}")
        else:
            self.notes.append(f"[{timestamp}] {note}")
    
    def update_status(self, new_status: WorkflowStatus, user: Optional[str] = None) -> None:
        """Update workflow status."""
        old_status = self.status
        self.status = new_status
        
        if new_status in [WorkflowStatus.PROCESSING, WorkflowStatus.SEQUENCED, WorkflowStatus.COMPLETED]:
            self.processing_date = datetime.utcnow()
            if user:
                self.processed_by = user
        
        self.add_note(f"Status changed from {old_status} to {new_status}", user)


@dataclass
class Sample:
    """Sample domain entity."""
    id: SampleId
    submission_id: str  # Foreign key to submission
    name: str
    measurements: Measurements
    qc_result: Optional[QCResult] = None
    processing_info: ProcessingInfo = field(default_factory=ProcessingInfo)
    
    # Metadata
    row_index: int = 0
    table_index: int = 0
    page_index: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def apply_qc(
        self,
        min_concentration: float = 10.0,
        min_volume: float = 20.0,
        min_quality_ratio: float = 1.8,
        evaluator: Optional[str] = None
    ) -> QCResult:
        """Apply quality control checks."""
        issues = []
        
        # Check concentration
        passed_conc = False
        if self.measurements.best_concentration:
            passed_conc = self.measurements.best_concentration.meets_threshold(min_concentration)
            if not passed_conc:
                issues.append(f"Low concentration: {self.measurements.best_concentration.value} {self.measurements.best_concentration.unit}")
        else:
            issues.append("No concentration measurement available")
        
        # Check volume
        passed_vol = False
        if self.measurements.volume:
            passed_vol = self.measurements.volume.meets_threshold(min_volume)
            if not passed_vol:
                issues.append(f"Low volume: {self.measurements.volume.value} {self.measurements.volume.unit}")
        else:
            issues.append("No volume measurement available")
        
        # Check quality ratio
        passed_ratio = False
        if self.measurements.a260_a280:
            passed_ratio = self.measurements.a260_a280.value >= min_quality_ratio
            if not passed_ratio:
                issues.append(f"Poor A260/A280 ratio: {self.measurements.a260_a280.value}")
        else:
            issues.append("No quality ratio measurement available")
        
        # Calculate score
        score_components = []
        if self.measurements.best_concentration:
            score_components.append(100 if passed_conc else 0)
        if self.measurements.volume:
            score_components.append(100 if passed_vol else 0)
        if self.measurements.a260_a280:
            # Scale ratio to 0-100 (1.8-2.0 is ideal)
            ratio_score = min(100, max(0, (self.measurements.a260_a280.value - 1.5) / 0.5 * 100))
            score_components.append(ratio_score)
        
        quality_score = None
        if score_components:
            quality_score = QualityScore(sum(score_components) / len(score_components))
        
        # Determine status
        if len(issues) == 0:
            status = QCStatus.PASSED
        elif len(issues) >= 2:
            status = QCStatus.FAILED
        else:
            status = QCStatus.WARNING
        
        self.qc_result = QCResult(
            status=status,
            score=quality_score,
            issues=issues,
            passed_concentration=passed_conc,
            passed_volume=passed_vol,
            passed_quality_ratio=passed_ratio,
            evaluated_at=datetime.utcnow(),
            evaluated_by=evaluator
        )
        
        self.updated_at = datetime.utcnow()
        return self.qc_result
    
    def update_location(self, location: StorageLocation, user: Optional[str] = None) -> None:
        """Update storage location."""
        old_location = self.processing_info.location
        self.processing_info.location = location
        self.processing_info.add_note(
            f"Location changed from {old_location.full_location if old_location else 'None'} to {location.full_location}",
            user
        )
        self.updated_at = datetime.utcnow()
    
    def is_ready_for_sequencing(self) -> bool:
        """Check if sample is ready for sequencing."""
        return (
            self.qc_result is not None and
            self.qc_result.status in [QCStatus.PASSED, QCStatus.WARNING] and
            self.processing_info.status == WorkflowStatus.PROCESSING
        )
    
    def mark_as_repeat(self, original_sample_id: SampleId) -> None:
        """Mark this sample as a repeat of another."""
        self.processing_info.add_note(f"Repeat of sample {original_sample_id}")
        self.updated_at = datetime.utcnow()
