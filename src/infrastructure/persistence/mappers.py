"""Mappers between domain models and ORM models."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ...domain.models.submission import Submission, SubmissionMetadata, PDFSource
from ...domain.models.sample import Sample, Measurements, QCResult, ProcessingInfo
from ...domain.models.value_objects import (
    SubmissionId, SampleId, WorkflowStatus, QCStatus,
    Concentration, Volume, QualityRatio, StorageLocation,
    Barcode, QualityScore, EmailAddress, Organism
)
from .models import SubmissionORM, SampleORM


class DomainMapper:
    """Maps between domain models and ORM models."""
    
    @staticmethod
    def submission_to_orm(submission: Submission) -> SubmissionORM:
        """Convert domain Submission to ORM model.
        
        Args:
            submission: Domain submission
            
        Returns:
            ORM submission
        """
        # Extract metadata fields
        metadata = submission.metadata
        
        # Convert lists to JSON strings
        pis_json = json.dumps(metadata.pis) if metadata.pis else None
        contacts_json = json.dumps(metadata.financial_contacts) if metadata.financial_contacts else None
        
        orm = SubmissionORM(
            id=submission.id,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            
            # PDF source
            source_file=str(submission.pdf_source.file_path),
            source_sha256=submission.pdf_source.file_hash,
            source_size=submission.pdf_source.file_size,
            source_mtime=submission.pdf_source.modification_time.timestamp(),
            page_count=submission.pdf_source.page_count,
            
            # PDF metadata
            title=submission.pdf_source.title,
            author=submission.pdf_source.author,
            subject=submission.pdf_source.subject,
            creator=submission.pdf_source.creator,
            producer=submission.pdf_source.producer,
            creation_date=submission.pdf_source.creation_date.isoformat() if submission.pdf_source.creation_date else None,
            
            # Extracted metadata
            identifier=metadata.identifier,
            as_of=metadata.as_of.isoformat() if metadata.as_of else None,
            expires_on=metadata.expires_on.isoformat() if metadata.expires_on else None,
            service_requested=metadata.service_requested,
            requester=metadata.requester,
            requester_email=metadata.requester_email.value if metadata.requester_email else None,
            phone=metadata.phone,
            lab=metadata.lab,
            billing_address=metadata.billing_address,
            storage_location=metadata.storage_location,
            pis=pis_json,
            financial_contacts=contacts_json,
            request_summary=metadata.request_summary,
            source_organism=metadata.organism.full_name if metadata.organism else None,
            human_dna="Yes" if metadata.contains_human_dna else "No" if metadata.contains_human_dna is not None else None,
            sample_buffer_json=metadata.sample_buffer,
            type_of_sample_json=metadata.submission_type
        )
        
        return orm
    
    @staticmethod
    def submission_from_orm(orm: SubmissionORM, samples: List[SampleORM]) -> Submission:
        """Convert ORM Submission to domain model.
        
        Args:
            orm: ORM submission
            samples: ORM samples
            
        Returns:
            Domain submission
        """
        # Parse JSON fields
        pis = json.loads(orm.pis) if orm.pis else []
        contacts = json.loads(orm.financial_contacts) if orm.financial_contacts else []
        
        # Create metadata
        metadata = SubmissionMetadata(
            identifier=orm.identifier,
            as_of=datetime.fromisoformat(orm.as_of) if orm.as_of else None,
            expires_on=datetime.fromisoformat(orm.expires_on) if orm.expires_on else None,
            service_requested=orm.service_requested,
            requester=orm.requester,
            requester_email=EmailAddress(orm.requester_email) if orm.requester_email else None,
            phone=orm.phone,
            lab=orm.lab,
            billing_address=orm.billing_address,
            storage_location=orm.storage_location,
            pis=pis,
            financial_contacts=contacts,
            request_summary=orm.request_summary,
            organism=DomainMapper._parse_organism(orm.source_organism),
            contains_human_dna=orm.human_dna == "Yes" if orm.human_dna else None,
            sample_buffer=orm.sample_buffer_json,
            submission_type=orm.type_of_sample_json
        )
        
        # Create PDF source
        pdf_source = PDFSource(
            file_path=Path(orm.source_file),
            file_hash=orm.source_sha256,
            file_size=orm.source_size or 0,
            modification_time=datetime.fromtimestamp(orm.source_mtime) if orm.source_mtime else datetime.utcnow(),
            page_count=orm.page_count,
            title=orm.title,
            author=orm.author,
            subject=orm.subject,
            creator=orm.creator,
            producer=orm.producer,
            creation_date=datetime.fromisoformat(orm.creation_date) if orm.creation_date else None
        )
        
        # Convert samples
        domain_samples = [
            DomainMapper.sample_from_orm(sample_orm)
            for sample_orm in samples
        ]
        
        return Submission(
            id=SubmissionId(orm.id),
            samples=domain_samples,
            metadata=metadata,
            pdf_source=pdf_source,
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )
    
    @staticmethod
    def sample_to_orm(sample: Sample) -> SampleORM:
        """Convert domain Sample to ORM model.
        
        Args:
            sample: Domain sample
            
        Returns:
            ORM sample
        """
        # Extract measurements
        measurements = sample.measurements
        
        # Extract QC result
        qc = sample.qc_result
        
        # Extract processing info
        proc = sample.processing_info
        
        # Convert notes list to string
        notes = "\n".join(proc.notes) if proc.notes else None
        
        orm = SampleORM(
            id=sample.id,
            submission_id=sample.submission_id,
            row_index=sample.row_index,
            table_index=sample.table_index,
            page_index=sample.page_index,
            name=sample.name,
            
            # Measurements
            volume_ul=measurements.volume.value if measurements.volume else None,
            qubit_ng_per_ul=measurements.qubit_concentration.value if measurements.qubit_concentration else None,
            nanodrop_ng_per_ul=measurements.nanodrop_concentration.value if measurements.nanodrop_concentration else None,
            a260_a280=measurements.a260_a280.value if measurements.a260_a280 else None,
            a260_a230=measurements.a260_a230.value if measurements.a260_a230 else None,
            
            # Tracking
            status=proc.status.value if proc.status else WorkflowStatus.RECEIVED.value,
            location=proc.location.full_location if proc.location else None,
            barcode=proc.barcode.value if proc.barcode else None,
            processing_date=proc.processing_date,
            processed_by=proc.processed_by,
            
            # QC
            qc_status=qc.status.value if qc else QCStatus.PENDING.value,
            qc_notes="; ".join(qc.issues) if qc and qc.issues else None,
            concentration_threshold_passed=qc.passed_concentration if qc else None,
            volume_threshold_passed=qc.passed_volume if qc else None,
            quality_score=qc.score.value if qc and qc.score else None,
            
            # Additional
            notes=notes,
            sequencing_run_id=proc.sequencing_run_id,
            data_path=proc.data_path,
            
            # Timestamps
            created_at=sample.created_at,
            updated_at=sample.updated_at
        )
        
        return orm
    
    @staticmethod
    def sample_from_orm(orm: SampleORM) -> Sample:
        """Convert ORM Sample to domain model.
        
        Args:
            orm: ORM sample
            
        Returns:
            Domain sample
        """
        # Create measurements
        measurements = Measurements(
            volume=Volume(orm.volume_ul) if orm.volume_ul else None,
            qubit_concentration=Concentration(orm.qubit_ng_per_ul) if orm.qubit_ng_per_ul else None,
            nanodrop_concentration=Concentration(orm.nanodrop_ng_per_ul) if orm.nanodrop_ng_per_ul else None,
            a260_a280=QualityRatio(orm.a260_a280) if orm.a260_a280 else None,
            a260_a230=QualityRatio(orm.a260_a230, "A260/A230") if orm.a260_a230 else None
        )
        
        # Create QC result if exists
        qc_result = None
        if orm.qc_status and orm.qc_status != "pending":
            issues = orm.qc_notes.split("; ") if orm.qc_notes else []
            qc_result = QCResult(
                status=QCStatus(orm.qc_status),
                score=QualityScore(orm.quality_score) if orm.quality_score else None,
                issues=issues,
                passed_concentration=orm.concentration_threshold_passed or False,
                passed_volume=orm.volume_threshold_passed or False,
                passed_quality_ratio=True  # Derive from issues if needed
            )
        
        # Create processing info
        processing_info = ProcessingInfo(
            status=WorkflowStatus(orm.status) if orm.status else WorkflowStatus.RECEIVED,
            location=StorageLocation.from_string(orm.location) if orm.location else None,
            barcode=Barcode(orm.barcode) if orm.barcode else None,
            processed_by=orm.processed_by,
            processing_date=orm.processing_date,
            sequencing_run_id=orm.sequencing_run_id,
            data_path=orm.data_path,
            notes=orm.notes.split("\n") if orm.notes else []
        )
        
        return Sample(
            id=SampleId(orm.id),
            submission_id=orm.submission_id,
            name=orm.name or "",
            measurements=measurements,
            qc_result=qc_result,
            processing_info=processing_info,
            row_index=orm.row_index,
            table_index=orm.table_index,
            page_index=orm.page_index,
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )
    
    @staticmethod
    def _parse_organism(organism_str: Optional[str]) -> Optional[Organism]:
        """Parse organism string into Organism value object."""
        if not organism_str:
            return None
        
        # Simple parsing - could be enhanced
        parts = organism_str.split()
        if not parts:
            return None
        
        return Organism(
            species=parts[0],
            strain=parts[1] if len(parts) > 1 else None,
            tissue=parts[2] if len(parts) > 2 else None
        )
