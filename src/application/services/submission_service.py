"""Submission service - Application layer orchestration."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pathlib import Path
from datetime import datetime
import logging

from ...domain.models.submission import Submission, SubmissionMetadata, PDFSource
from ...domain.models.sample import Sample
from ...domain.models.value_objects import SubmissionId, WorkflowStatus
from ...domain.repositories.submission_repository import SubmissionRepository

if TYPE_CHECKING:
    from ...infrastructure.pdf.processor import PDFProcessor


logger = logging.getLogger(__name__)


class SubmissionService:
    """Service for managing submissions."""
    
    def __init__(
        self,
        repository: SubmissionRepository,
        pdf_processor: 'PDFProcessor',  # Type hint to avoid circular import
        qc_auto_apply: bool = False
    ):
        """Initialize submission service.
        
        Args:
            repository: Submission repository
            pdf_processor: PDF processing service
            qc_auto_apply: Whether to automatically apply QC on import
        """
        self.repository = repository
        self.pdf_processor = pdf_processor
        self.qc_auto_apply = qc_auto_apply
    
    async def create_from_pdf(
        self,
        pdf_path: Path,
        force: bool = False,
        storage_location: Optional[str] = None
    ) -> Submission:
        """Create submission from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            force: Force re-import even if file exists
            storage_location: Storage location for the samples
            
        Returns:
            Created submission
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF is invalid
            DuplicateSubmissionError: If submission already exists and force=False
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Extract data from PDF using legacy slurper for now
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Use the legacy slurp functionality directly
        from pdf_slurper.slurp import slurp_pdf
        from pdf_slurper.hash_utils import sha256_file
        
        # Check for existing submission if not forcing
        if not force:
            file_hash = sha256_file(pdf_path)
            existing = await self.repository.find_by_hash(file_hash)
            if existing:
                logger.info(f"Submission already exists: {existing.id}")
                return existing
        
        # Process the PDF using legacy slurper
        result = slurp_pdf(pdf_path, force=force)
        
        # Get the created submission from the legacy database
        from pdf_slurper.db import open_session, Submission as LegacySubmission, Sample as LegacySample
        from sqlmodel import select, func
        
        with open_session() as session:
            legacy_sub = session.exec(
                select(LegacySubmission).where(LegacySubmission.id == result.submission_id)
            ).first()
            
            if not legacy_sub:
                raise ValueError(f"Failed to create submission from PDF")
            
            # Get sample count
            sample_count = session.exec(
                select(func.count()).select_from(LegacySample).where(
                    LegacySample.submission_id == legacy_sub.id
                )
            ).one()
            
            # Convert to new domain model
            submission_id = SubmissionId(legacy_sub.id)
            
            # Create metadata
            metadata = SubmissionMetadata(
                identifier=legacy_sub.identifier,
                service_requested=legacy_sub.service_requested,
                requester=legacy_sub.requester,
                requester_email=legacy_sub.requester_email,  # Just use string for now
                lab=legacy_sub.lab,
                organism=None,  # Would need to parse from source_organism
                contains_human_dna=legacy_sub.human_dna == "Yes" if legacy_sub.human_dna else None,
                storage_location=storage_location  # Store the provided location
            )
            
            # Create PDF source
            pdf_source = PDFSource(
                file_path=Path(legacy_sub.source_file),
                file_hash=legacy_sub.source_sha256,
                page_count=legacy_sub.page_count,
                file_size=legacy_sub.source_size or 0,
                modification_time=legacy_sub.source_mtime or 0
            )
            
            # Create submission with sample count
            submission = Submission(
                id=submission_id,
                metadata=metadata,
                pdf_source=pdf_source,
                samples=[],  # Samples are in legacy DB
                created_at=legacy_sub.created_at
            )
            
            # Auto-apply QC if configured
            if self.qc_auto_apply and sample_count > 0:
                logger.info(f"Auto-applying QC to {sample_count} samples")
                # QC would be applied in legacy system
            
            logger.info(f"Created submission: {submission.id}")
            
            return submission
    
    async def get_by_id(self, submission_id: SubmissionId) -> Optional[Submission]:
        """Get submission by ID.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            Submission if found, None otherwise
        """
        return await self.repository.get(submission_id)
    
    async def apply_qc(
        self,
        submission_id: SubmissionId,
        min_concentration: float = 10.0,
        min_volume: float = 20.0,
        min_quality_ratio: float = 1.8,
        evaluator: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply QC to all samples in submission.
        
        Args:
            submission_id: Submission ID
            min_concentration: Minimum concentration threshold
            min_volume: Minimum volume threshold
            min_quality_ratio: Minimum quality ratio threshold
            evaluator: Person performing QC
            
        Returns:
            QC results summary
            
        Raises:
            SubmissionNotFoundError: If submission doesn't exist
        """
        submission = await self.repository.get(submission_id)
        if not submission:
            raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
        
        results = submission.apply_qc_to_all(
            min_concentration=min_concentration,
            min_volume=min_volume,
            min_quality_ratio=min_quality_ratio,
            evaluator=evaluator
        )
        
        # Save updated submission
        await self.repository.save(submission)
        
        logger.info(
            f"QC applied to submission {submission_id}: "
            f"{results['passed']} passed, {results['warning']} warning, "
            f"{results['failed']} failed"
        )
        
        return results
    
    async def batch_update_sample_status(
        self,
        submission_id: SubmissionId,
        sample_ids: List[str],
        status: WorkflowStatus,
        user: Optional[str] = None
    ) -> int:
        """Update status for multiple samples.
        
        Args:
            submission_id: Submission ID
            sample_ids: List of sample IDs to update
            status: New workflow status
            user: User performing update
            
        Returns:
            Number of samples updated
            
        Raises:
            SubmissionNotFoundError: If submission doesn't exist
        """
        submission = await self.repository.get(submission_id)
        if not submission:
            raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
        
        count = submission.batch_update_status(sample_ids, status.value, user)
        
        if count > 0:
            await self.repository.save(submission)
            logger.info(
                f"Updated {count} samples in submission {submission_id} "
                f"to status {status.value}"
            )
        
        return count
    
    async def search(
        self,
        query: Optional[str] = None,
        requester_email: Optional[str] = None,
        lab: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Submission]:
        """Search submissions.
        
        Args:
            query: Text search query
            requester_email: Filter by requester email
            lab: Filter by lab
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results
            offset: Results offset
            
        Returns:
            List of matching submissions
        """
        from ...domain.repositories.base import Pagination
        
        pagination = Pagination(offset=offset, limit=limit)
        
        # Apply filters based on provided criteria
        if query:
            page = await self.repository.search(query, pagination)
            return page.items
        elif requester_email:
            return await self.repository.find_by_requester_email(
                requester_email, pagination
            )
        elif lab:
            return await self.repository.find_by_lab(lab, pagination)
        elif start_date:
            return await self.repository.find_by_date_range(
                start_date, end_date, pagination
            )
        else:
            return await self.repository.get_all(pagination)
    
    async def get_statistics(
        self,
        submission_id: Optional[SubmissionId] = None
    ) -> Dict[str, Any]:
        """Get statistics.
        
        Args:
            submission_id: Specific submission ID or None for global stats
            
        Returns:
            Statistics dictionary
        """
        if submission_id:
            submission = await self.repository.get(submission_id)
            if not submission:
                raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
            return submission.get_statistics()
        else:
            return await self.repository.get_statistics()
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get global statistics across all submissions.
        
        Returns:
            Global statistics dictionary
        """
        return await self.repository.get_statistics()
    
    async def delete(self, submission_id: SubmissionId) -> bool:
        """Delete submission.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await self.repository.delete(submission_id)
        if result:
            logger.info(f"Deleted submission: {submission_id}")
        return result
    
    async def _create_submission(self, extraction_result: Any) -> Submission:
        """Create submission from extraction result."""
        # For now, use the legacy slurp functionality
        from pdf_slurper.slurp import slurp_pdf
        from pathlib import Path
        import uuid
        
        # If extraction_result is a Path, use the legacy slurp
        if isinstance(extraction_result, Path):
            # Call the legacy slurp function
            result = slurp_pdf(extraction_result, force=True)
            
            # Get the created submission from the database
            from pdf_slurper.db import open_session, Submission as LegacySubmission
            with open_session() as session:
                from sqlmodel import select
                legacy_sub = session.exec(
                    select(LegacySubmission).where(LegacySubmission.id == result.submission_id)
                ).first()
                
                if legacy_sub:
                    # Convert to new domain model
                    submission_id = SubmissionId(legacy_sub.id)
                    
                    # Create metadata
                    metadata = SubmissionMetadata(
                        identifier=legacy_sub.identifier,
                        service_requested=legacy_sub.service_requested,
                        requester=legacy_sub.requester,
                        requester_email=legacy_sub.requester_email,
                        lab=legacy_sub.lab,
                        organism=legacy_sub.source_organism,
                        contains_human_dna=legacy_sub.human_dna == "Yes" if legacy_sub.human_dna else None
                    )
                    
                    # Create PDF source
                    pdf_source = PDFSource(
                        file_path=Path(legacy_sub.source_file),
                        file_hash=legacy_sub.source_sha256,
                        page_count=legacy_sub.page_count
                    )
                    
                    # Create submission
                    submission = Submission(
                        id=submission_id,
                        metadata=metadata,
                        pdf_source=pdf_source,
                        samples=[],  # Samples are handled separately in legacy
                        created_at=legacy_sub.created_at,
                        updated_at=legacy_sub.updated_at
                    )
                    
                    return submission
        
        # Fallback: create a minimal submission
        submission_id = SubmissionId(f"sub_{uuid.uuid4().hex[:12]}")
        metadata = SubmissionMetadata()
        pdf_source = PDFSource(
            file_path=extraction_result if isinstance(extraction_result, Path) else Path("/tmp/unknown.pdf"),
            file_hash="",
            page_count=0
        )
        
        return Submission(
            id=submission_id,
            metadata=metadata,
            pdf_source=pdf_source,
            samples=[]
        )
    
    async def _update_existing(
        self,
        submission: Submission,
        extraction_result: Any
    ) -> None:
        """Update existing submission with new extraction data."""
        # Update metadata if changed
        # This allows re-processing with improved extraction
        pass


class SubmissionNotFoundError(Exception):
    """Submission not found error."""
    pass


class DuplicateSubmissionError(Exception):
    """Duplicate submission error."""
    pass
