"""Submission service - Application layer orchestration."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pathlib import Path
from datetime import datetime
import logging

from ...domain.models.submission import Submission, SubmissionMetadata, PDFSource
from ...domain.models.sample import Sample, Measurements
from ...domain.models.value_objects import (
    SubmissionId, SampleId, WorkflowStatus, Organism,
    Concentration, Volume, QualityRatio, EmailAddress
)
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
        
        # Process PDF using the new PDF processor
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Process the PDF to extract data
        pdf_data = await self.pdf_processor.process(pdf_path)
        file_hash = pdf_data["file_hash"]
        
        # Check for existing submission if not forcing
        if not force:
            existing = await self.repository.find_by_hash(file_hash)
            if existing:
                logger.info(f"Submission already exists: {existing.id}")
                return existing
        
        # Generate new submission ID
        import uuid
        submission_id = SubmissionId(str(uuid.uuid4()))
        
        # Create metadata from extracted PDF data
        pdf_metadata = pdf_data.get("metadata", {})
        
        # Parse date strings if present
        from datetime import datetime
        as_of_str = pdf_metadata.get("as_of")
        expires_str = pdf_metadata.get("expires_on")
        
        as_of = None
        expires_on = None
        if as_of_str:
            try:
                # Try to parse common date formats
                for fmt in ["%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        as_of = datetime.strptime(as_of_str, fmt)
                        break
                    except:
                        pass
            except:
                pass
        
        if expires_str:
            try:
                for fmt in ["%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        expires_on = datetime.strptime(expires_str, fmt)
                        break
                    except:
                        pass
            except:
                pass
        
        # Handle PIs and financial contacts as lists
        pis = pdf_metadata.get("pis", "")
        if isinstance(pis, str) and pis:
            pis = [p.strip() for p in pis.split(",") if p.strip()]
        else:
            pis = []
            
        financial_contacts = pdf_metadata.get("financial_contacts", "")
        if isinstance(financial_contacts, str) and financial_contacts:
            financial_contacts = [c.strip() for c in financial_contacts.split(",") if c.strip()]
        else:
            financial_contacts = []
        
        # Create comprehensive metadata from all extracted fields
        metadata = SubmissionMetadata(
            identifier=pdf_metadata.get("identifier", ""),
            service_requested=pdf_metadata.get("service_requested", ""),
            requester=pdf_metadata.get("requester", ""),
            requester_email=EmailAddress(value=pdf_metadata.get("requester_email")) if pdf_metadata.get("requester_email") else None,
            lab=pdf_metadata.get("lab", ""),
            organism=Organism(
                species=pdf_metadata.get("source_organism") or pdf_metadata.get("organism")
            ) if (pdf_metadata.get("source_organism") or pdf_metadata.get("organism")) else None,
            contains_human_dna=pdf_metadata.get("contains_human_dna") or (pdf_metadata.get("human_dna") == "Yes"),
            storage_location=storage_location,
            # Date fields
            as_of=as_of,
            expires_on=expires_on,
            # Contact fields
            phone=pdf_metadata.get("phone"),
            billing_address=pdf_metadata.get("billing_address"),
            pis=pis,
            financial_contacts=financial_contacts,
            # Additional fields
            request_summary=pdf_metadata.get("request_summary"),
            forms_text=pdf_metadata.get("forms_text"),
            will_submit_dna_for=pdf_metadata.get("will_submit_dna_for"),
            type_of_sample=pdf_metadata.get("type_of_sample"),
            sample_buffer=pdf_metadata.get("sample_buffer"),
            source_organism=pdf_metadata.get("source_organism"),
            notes=pdf_metadata.get("notes"),
            # Flow Cell and Sequencing Parameters
            flow_cell_type=pdf_metadata.get("flow_cell_type"),
            genome_size=pdf_metadata.get("genome_size"),
            coverage_needed=pdf_metadata.get("coverage_needed"),
            flow_cells_count=pdf_metadata.get("flow_cells_count"),
            # Bioinformatics and Data Delivery
            basecalling=pdf_metadata.get("basecalling"),
            file_format=pdf_metadata.get("file_format"),
            data_delivery=pdf_metadata.get("data_delivery")
        )
        
        # Create PDF source
        pdf_source = PDFSource(
            file_path=pdf_path,
            file_hash=file_hash,
            page_count=pdf_data.get("page_count", 0),
            file_size=pdf_path.stat().st_size,
            modification_time=datetime.fromtimestamp(pdf_path.stat().st_mtime)
        )
        
        # Create samples from extracted data
        samples = []
        for sample_data in pdf_data.get("samples", []):
            sample_id = SampleId(str(uuid.uuid4()))
            
            # Get concentration from either qubit or nanodrop
            qubit_conc = sample_data.get("qubit_ng_per_ul")
            nanodrop_conc = sample_data.get("nanodrop_ng_per_ul") or sample_data.get("concentration")
            
            measurements = Measurements(
                qubit_concentration=Concentration(
                    value=qubit_conc,
                    unit="ng/µL"
                ) if qubit_conc else None,
                nanodrop_concentration=Concentration(
                    value=nanodrop_conc,
                    unit="ng/µL"
                ) if nanodrop_conc else None,
                volume=Volume(
                    value=sample_data.get("volume_ul", 0),
                    unit="µL"
                ) if sample_data.get("volume_ul") else None,
                a260_a280=QualityRatio(
                    ratio_260_280=sample_data.get("a260_a280")
                ) if sample_data.get("a260_a280") else None
            )
            sample = Sample(
                id=sample_id,
                submission_id=submission_id,
                name=sample_data.get("name", ""),
                measurements=measurements
            )
            samples.append(sample)
        
        # Create submission
        submission = Submission(
            id=submission_id,
            metadata=metadata,
            pdf_source=pdf_source,
            samples=samples,
            created_at=datetime.utcnow()
        )
        
        # Save to repository
        await self.repository.save(submission)
        
        # Auto-apply QC if configured
        if self.qc_auto_apply and len(samples) > 0:
            logger.info(f"Auto-applying QC to {len(samples)} samples")
            # TODO: Implement QC application
        
        logger.info(f"Created submission: {submission.id} with {len(samples)} samples")
        
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
    
    async def update(self, submission: Submission) -> Submission:
        """Update an existing submission.
        
        Args:
            submission: Updated submission
            
        Returns:
            Updated submission
        """
        return await self.repository.save(submission)
    
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
    
    # Removed _create_submission method that used legacy code
    # The create_from_pdf method now handles all submission creation
    
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
