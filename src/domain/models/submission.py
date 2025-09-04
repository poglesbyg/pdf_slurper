"""Submission domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from .value_objects import (
    SubmissionId, EmailAddress, Organism, DateRange
)
from .sample import Sample


@dataclass
class SubmissionMetadata:
    """Submission metadata from PDF."""
    identifier: Optional[str] = None
    as_of: Optional[datetime] = None
    expires_on: Optional[datetime] = None
    service_requested: Optional[str] = None
    requester: Optional[str] = None
    requester_email: Optional[EmailAddress] = None
    phone: Optional[str] = None
    lab: Optional[str] = None
    billing_address: Optional[str] = None
    pis: List[str] = field(default_factory=list)
    financial_contacts: List[str] = field(default_factory=list)
    request_summary: Optional[str] = None
    organism: Optional[Organism] = None
    contains_human_dna: Optional[bool] = None
    sample_buffer: Optional[str] = None
    submission_type: Optional[str] = None
    storage_location: Optional[str] = None  # Location where samples are stored
    # Additional comprehensive fields from PDF extraction
    forms_text: Optional[str] = None
    will_submit_dna_for: Optional[str] = None
    type_of_sample: Optional[str] = None
    source_organism: Optional[str] = None
    notes: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if submission has expired."""
        if self.expires_on:
            return datetime.utcnow() > self.expires_on
        return False


@dataclass
class PDFSource:
    """PDF source information."""
    file_path: Path
    file_hash: str
    file_size: int
    modification_time: datetime
    page_count: int
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    
    @property
    def fingerprint(self) -> str:
        """Get unique fingerprint for the PDF."""
        return f"{self.file_hash}:{self.file_size}:{self.modification_time.timestamp()}"


@dataclass
class Submission:
    """Submission domain entity."""
    id: SubmissionId
    samples: List[Sample]
    metadata: SubmissionMetadata
    pdf_source: PDFSource
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def sample_count(self) -> int:
        """Get total number of samples."""
        return len(self.samples)
    
    @property
    def is_complete(self) -> bool:
        """Check if all samples are completed."""
        from .value_objects import WorkflowStatus
        return all(
            s.processing_info.status == WorkflowStatus.COMPLETED
            for s in self.samples
        )
    
    def get_sample_by_id(self, sample_id: str) -> Optional[Sample]:
        """Get sample by ID."""
        for sample in self.samples:
            if sample.id == sample_id:
                return sample
        return None
    
    def get_samples_by_status(self, status: str) -> List[Sample]:
        """Get samples with specific workflow status."""
        return [
            s for s in self.samples
            if s.processing_info.status == status
        ]
    
    def get_samples_needing_qc(self) -> List[Sample]:
        """Get samples that haven't been QC'd."""
        return [
            s for s in self.samples
            if s.qc_result is None
        ]
    
    def get_failed_samples(self) -> List[Sample]:
        """Get samples that failed QC."""
        from .value_objects import QCStatus
        return [
            s for s in self.samples
            if s.qc_result and s.qc_result.status == QCStatus.FAILED
        ]
    
    def apply_qc_to_all(
        self,
        min_concentration: float = 10.0,
        min_volume: float = 20.0,
        min_quality_ratio: float = 1.8,
        evaluator: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply QC to all samples."""
        results = {
            'total': len(self.samples),
            'passed': 0,
            'warning': 0,
            'failed': 0,
            'skipped': 0
        }
        
        from .value_objects import QCStatus
        
        for sample in self.samples:
            if sample.qc_result is not None:
                results['skipped'] += 1
                continue
            
            qc_result = sample.apply_qc(
                min_concentration=min_concentration,
                min_volume=min_volume,
                min_quality_ratio=min_quality_ratio,
                evaluator=evaluator
            )
            
            if qc_result.status == QCStatus.PASSED:
                results['passed'] += 1
            elif qc_result.status == QCStatus.WARNING:
                results['warning'] += 1
            elif qc_result.status == QCStatus.FAILED:
                results['failed'] += 1
        
        self.updated_at = datetime.utcnow()
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get submission statistics."""
        from .value_objects import WorkflowStatus, QCStatus
        
        stats = {
            'total_samples': len(self.samples),
            'workflow_status': {},
            'qc_status': {},
            'average_concentration': None,
            'average_volume': None,
            'average_quality_score': None,
            'samples_with_location': 0,
            'samples_processed': 0,
        }
        
        concentrations = []
        volumes = []
        quality_scores = []
        
        for sample in self.samples:
            # Workflow status
            status = sample.processing_info.status.value
            stats['workflow_status'][status] = stats['workflow_status'].get(status, 0) + 1
            
            # QC status
            if sample.qc_result:
                qc_status = sample.qc_result.status.value
                stats['qc_status'][qc_status] = stats['qc_status'].get(qc_status, 0) + 1
                
                if sample.qc_result.score:
                    quality_scores.append(sample.qc_result.score.value)
            else:
                stats['qc_status']['pending'] = stats['qc_status'].get('pending', 0) + 1
            
            # Measurements
            if sample.measurements.best_concentration:
                concentrations.append(sample.measurements.best_concentration.value)
            if sample.measurements.volume:
                volumes.append(sample.measurements.volume.value)
            
            # Location and processing
            if sample.processing_info.location:
                stats['samples_with_location'] += 1
            if sample.processing_info.processing_date:
                stats['samples_processed'] += 1
        
        # Calculate averages
        if concentrations:
            stats['average_concentration'] = sum(concentrations) / len(concentrations)
        if volumes:
            stats['average_volume'] = sum(volumes) / len(volumes)
        if quality_scores:
            stats['average_quality_score'] = sum(quality_scores) / len(quality_scores)
        
        return stats
    
    def batch_update_status(
        self,
        sample_ids: List[str],
        new_status: str,
        user: Optional[str] = None
    ) -> int:
        """Update status for multiple samples."""
        from .value_objects import WorkflowStatus
        
        count = 0
        status = WorkflowStatus(new_status)
        
        for sample in self.samples:
            if sample.id in sample_ids:
                sample.processing_info.update_status(status, user)
                count += 1
        
        if count > 0:
            self.updated_at = datetime.utcnow()
        
        return count
    
    def add_sample(self, sample: Sample) -> None:
        """Add a sample to the submission."""
        self.samples.append(sample)
        self.updated_at = datetime.utcnow()
    
    def remove_sample(self, sample_id: str) -> bool:
        """Remove a sample from the submission."""
        initial_count = len(self.samples)
        self.samples = [s for s in self.samples if s.id != sample_id]
        
        if len(self.samples) < initial_count:
            self.updated_at = datetime.utcnow()
            return True
        return False
