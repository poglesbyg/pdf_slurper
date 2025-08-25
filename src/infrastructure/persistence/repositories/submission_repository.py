"""SQLAlchemy implementation of SubmissionRepository."""

import logging
from typing import Optional, List
from datetime import datetime

from sqlmodel import select, col
from sqlalchemy import func

from ....domain.models.submission import Submission
from ....domain.models.value_objects import SubmissionId
from ....domain.repositories.submission_repository import SubmissionRepository
from ....domain.repositories.base import Pagination, Page
from ..models import SubmissionORM, SampleORM
from ..mappers import DomainMapper
from ..database import Database

logger = logging.getLogger(__name__)


class SQLSubmissionRepository(SubmissionRepository):
    """SQL implementation of submission repository."""
    
    def __init__(self, database: Database):
        """Initialize repository.
        
        Args:
            database: Database instance
        """
        self.database = database
        self.mapper = DomainMapper()
    
    async def get(self, id: SubmissionId) -> Optional[Submission]:
        """Get submission by ID.
        
        Args:
            id: Submission ID
            
        Returns:
            Submission if found, None otherwise
        """
        with self.database.get_session() as session:
            # Get submission
            orm = session.get(SubmissionORM, id)
            if not orm:
                return None
            
            # Get samples
            stmt = select(SampleORM).where(SampleORM.submission_id == id)
            samples = list(session.exec(stmt))
            
            # Map to domain
            return self.mapper.submission_from_orm(orm, samples)
    
    async def get_all(self, pagination: Optional[Pagination] = None) -> List[Submission]:
        """Get all submissions.
        
        Args:
            pagination: Pagination parameters
            
        Returns:
            List of submissions
        """
        pagination = pagination or Pagination()
        
        with self.database.get_session() as session:
            # Query submissions
            stmt = select(SubmissionORM).order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples for each submission
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return submissions
    
    async def save(self, entity: Submission) -> Submission:
        """Save submission.
        
        Args:
            entity: Submission to save
            
        Returns:
            Saved submission
        """
        with self.database.get_session() as session:
            # Check if exists
            existing = session.get(SubmissionORM, entity.id)
            
            # Map to ORM
            orm = self.mapper.submission_to_orm(entity)
            
            if existing:
                # Update existing
                for key, value in orm.model_dump(exclude={'id', 'samples'}).items():
                    setattr(existing, key, value)
                session.add(existing)
                
                # Update samples
                # Delete existing samples
                stmt = select(SampleORM).where(SampleORM.submission_id == entity.id)
                for sample_orm in session.exec(stmt):
                    session.delete(sample_orm)
            else:
                # Create new
                session.add(orm)
            
            # Add samples
            for sample in entity.samples:
                sample_orm = self.mapper.sample_to_orm(sample)
                session.add(sample_orm)
            
            session.commit()
            
            logger.info(f"Saved submission: {entity.id}")
            return entity
    
    async def delete(self, id: SubmissionId) -> bool:
        """Delete submission.
        
        Args:
            id: Submission ID
            
        Returns:
            True if deleted, False if not found
        """
        deleted_from_legacy = False
        deleted_from_new = False
        
        # Try to delete from legacy database
        try:
            from pdf_slurper.db import open_session, Submission as LegacySubmission, Sample as LegacySample
            from sqlmodel import select as legacy_select
            
            with open_session() as legacy_session:
                # Find the legacy submission
                legacy_stmt = legacy_select(LegacySubmission).where(LegacySubmission.id == str(id))
                legacy_submission = legacy_session.exec(legacy_stmt).first()
                
                if legacy_submission:
                    # Delete legacy samples
                    sample_stmt = legacy_select(LegacySample).where(LegacySample.submission_id == str(id))
                    for legacy_sample in legacy_session.exec(sample_stmt):
                        legacy_session.delete(legacy_sample)
                    
                    # Delete legacy submission
                    legacy_session.delete(legacy_submission)
                    legacy_session.commit()
                    logger.info(f"Deleted from legacy database: {id}")
                    deleted_from_legacy = True
        except Exception as e:
            logger.warning(f"Failed to delete from legacy database: {e}")
        
        # Try to delete from new database
        with self.database.get_session() as session:
            orm = session.get(SubmissionORM, str(id))
            if orm:
                # Delete samples first (cascade should handle this)
                stmt = select(SampleORM).where(SampleORM.submission_id == str(id))
                for sample_orm in session.exec(stmt):
                    session.delete(sample_orm)
                
                # Delete submission
                session.delete(orm)
                session.commit()
                
                logger.info(f"Deleted from new database: {id}")
                deleted_from_new = True
        
        # Return True if deleted from either database
        return deleted_from_legacy or deleted_from_new
    
    async def exists(self, id: SubmissionId) -> bool:
        """Check if submission exists.
        
        Args:
            id: Submission ID
            
        Returns:
            True if exists, False otherwise
        """
        with self.database.get_session() as session:
            orm = session.get(SubmissionORM, id)
            return orm is not None
    
    async def count(self) -> int:
        """Count total submissions.
        
        Returns:
            Total count
        """
        with self.database.get_session() as session:
            stmt = select(func.count()).select_from(SubmissionORM)
            return session.exec(stmt).one()
    
    async def find_by_hash(self, file_hash: str) -> Optional[Submission]:
        """Find submission by PDF file hash.
        
        Args:
            file_hash: File hash
            
        Returns:
            Submission if found
        """
        with self.database.get_session() as session:
            stmt = select(SubmissionORM).where(SubmissionORM.source_sha256 == file_hash)
            orm = session.exec(stmt).first()
            
            if not orm:
                return None
            
            # Get samples
            sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
            samples = list(session.exec(sample_stmt))
            
            return self.mapper.submission_from_orm(orm, samples)
    
    async def find_by_identifier(self, identifier: str) -> Optional[Submission]:
        """Find submission by business identifier.
        
        Args:
            identifier: Business identifier
            
        Returns:
            Submission if found
        """
        with self.database.get_session() as session:
            stmt = select(SubmissionORM).where(SubmissionORM.identifier == identifier)
            orm = session.exec(stmt).first()
            
            if not orm:
                return None
            
            # Get samples
            sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
            samples = list(session.exec(sample_stmt))
            
            return self.mapper.submission_from_orm(orm, samples)
    
    async def find_by_requester_email(
        self,
        email: str,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions by requester email.
        
        Args:
            email: Email address
            pagination: Pagination parameters
            
        Returns:
            List of submissions
        """
        pagination = pagination or Pagination()
        
        with self.database.get_session() as session:
            stmt = select(SubmissionORM).where(SubmissionORM.requester_email == email)
            stmt = stmt.order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return submissions
    
    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions within date range.
        
        Args:
            start_date: Start date
            end_date: End date (optional)
            pagination: Pagination parameters
            
        Returns:
            List of submissions
        """
        pagination = pagination or Pagination()
        
        with self.database.get_session() as session:
            stmt = select(SubmissionORM).where(SubmissionORM.created_at >= start_date)
            
            if end_date:
                stmt = stmt.where(SubmissionORM.created_at <= end_date)
            
            stmt = stmt.order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return submissions
    
    async def find_by_lab(
        self,
        lab: str,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions by lab.
        
        Args:
            lab: Lab name
            pagination: Pagination parameters
            
        Returns:
            List of submissions
        """
        pagination = pagination or Pagination()
        
        with self.database.get_session() as session:
            stmt = select(SubmissionORM).where(SubmissionORM.lab.ilike(f"%{lab}%"))
            stmt = stmt.order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return submissions
    
    async def find_with_samples_needing_qc(
        self,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions with samples that need QC.
        
        Args:
            pagination: Pagination parameters
            
        Returns:
            List of submissions
        """
        pagination = pagination or Pagination()
        
        with self.database.get_session() as session:
            # Find submissions with samples in pending QC status
            subquery = select(SampleORM.submission_id).where(
                SampleORM.qc_status == "pending"
            ).distinct()
            
            stmt = select(SubmissionORM).where(
                SubmissionORM.id.in_(subquery)
            )
            stmt = stmt.order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return submissions
    
    async def find_expired(
        self,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find expired submissions.
        
        Args:
            pagination: Pagination parameters
            
        Returns:
            List of expired submissions
        """
        pagination = pagination or Pagination()
        current_date = datetime.utcnow().isoformat()
        
        with self.database.get_session() as session:
            stmt = select(SubmissionORM).where(
                SubmissionORM.expires_on < current_date
            )
            stmt = stmt.order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return submissions
    
    async def search(
        self,
        query: str,
        pagination: Optional[Pagination] = None
    ) -> Page[Submission]:
        """Search submissions by text query.
        
        Args:
            query: Search query
            pagination: Pagination parameters
            
        Returns:
            Page of results
        """
        pagination = pagination or Pagination()
        
        with self.database.get_session() as session:
            # Search in multiple fields
            search_term = f"%{query}%"
            stmt = select(SubmissionORM).where(
                col(SubmissionORM.identifier).ilike(search_term) |
                col(SubmissionORM.title).ilike(search_term) |
                col(SubmissionORM.requester).ilike(search_term) |
                col(SubmissionORM.lab).ilike(search_term) |
                col(SubmissionORM.service_requested).ilike(search_term)
            )
            
            # Count total
            count_stmt = select(func.count()).select_from(SubmissionORM).where(
                col(SubmissionORM.identifier).ilike(search_term) |
                col(SubmissionORM.title).ilike(search_term) |
                col(SubmissionORM.requester).ilike(search_term) |
                col(SubmissionORM.lab).ilike(search_term) |
                col(SubmissionORM.service_requested).ilike(search_term)
            )
            total = session.exec(count_stmt).one()
            
            # Apply pagination
            stmt = stmt.order_by(SubmissionORM.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            submissions = []
            for orm in session.exec(stmt):
                # Get samples
                sample_stmt = select(SampleORM).where(SampleORM.submission_id == orm.id)
                samples = list(session.exec(sample_stmt))
                
                # Map to domain
                submission = self.mapper.submission_from_orm(orm, samples)
                submissions.append(submission)
            
            return Page(
                items=submissions,
                total=total,
                offset=pagination.offset,
                limit=pagination.limit
            )
    
    async def get_statistics(self) -> dict:
        """Get global statistics across all submissions.
        
        Returns:
            Statistics dictionary
        """
        with self.database.get_session() as session:
            # Count v2 submissions  
            submission_count_v2 = session.exec(
                select(func.count()).select_from(SubmissionORM)
            ).one()
            
            # Count v2 samples
            sample_count_v2 = session.exec(
                select(func.count()).select_from(SampleORM)
            ).one()
            
            # Also count legacy submissions and samples
            from pdf_slurper.db import open_session, Submission as LegacySubmission, Sample as LegacySample
            from sqlmodel import select as legacy_select, func as legacy_func
            
            with open_session() as legacy_session:
                submission_count_legacy = legacy_session.exec(
                    legacy_select(legacy_func.count()).select_from(LegacySubmission)
                ).one()
                
                sample_count_legacy = legacy_session.exec(
                    legacy_select(legacy_func.count()).select_from(LegacySample)
                ).one()
            
            # Combine counts
            submission_count = submission_count_v2 + submission_count_legacy
            sample_count = sample_count_v2 + sample_count_legacy
            
            # Get workflow and QC status counts from legacy samples
            status_counts = {}
            qc_counts = {}
            
            with open_session() as legacy_session:
                # Count by workflow status from legacy samples (column is named 'status')
                for status in ["received", "processing", "sequenced", "completed", "failed"]:
                    count = legacy_session.exec(
                        legacy_select(legacy_func.count()).select_from(LegacySample).where(
                            LegacySample.status == status
                        )
                    ).one()
                    status_counts[status] = count or 0
                
                # Count NULL status as 'pending'
                null_status_count = legacy_session.exec(
                    legacy_select(legacy_func.count()).select_from(LegacySample).where(
                        LegacySample.status == None
                    )
                ).one()
                status_counts["pending"] = status_counts.get("pending", 0) + (null_status_count or 0)
                
                # Count by QC status from legacy samples
                for qc_status in ["pending", "passed", "warning", "failed"]:
                    count = legacy_session.exec(
                        legacy_select(legacy_func.count()).select_from(LegacySample).where(
                            LegacySample.qc_status == qc_status
                        )
                    ).one()
                    qc_counts[qc_status] = count or 0
                
                # Count NULL qc_status as 'pending'
                null_qc_count = legacy_session.exec(
                    legacy_select(legacy_func.count()).select_from(LegacySample).where(
                        LegacySample.qc_status == None
                    )
                ).one()
                qc_counts["pending"] = qc_counts.get("pending", 0) + (null_qc_count or 0)
                
                # Calculate averages from legacy samples
                avg_volume = legacy_session.exec(
                    legacy_select(legacy_func.avg(LegacySample.volume_ul)).select_from(LegacySample)
                ).one() or 0
                
                avg_concentration = legacy_session.exec(
                    legacy_select(legacy_func.avg(LegacySample.qubit_ng_per_ul)).select_from(LegacySample)
                ).one() or 0
            
            print(f"DEBUG: Final status_counts = {status_counts}")
            print(f"DEBUG: Final qc_counts = {qc_counts}")
            
            return {
                "total_submissions": submission_count,
                "total_samples": sample_count,
                "workflow_status": status_counts,  # Renamed to match frontend expectations
                "qc_status": qc_counts,  # Renamed to match frontend expectations
                "average_volume": float(avg_volume) if avg_volume else 0,
                "average_concentration": float(avg_concentration) if avg_concentration else 0,
                "average_quality_score": None,  # Would need to calculate this
                "samples_with_location": 0,  # Would need to query for this
                "samples_processed": status_counts.get("processing", 0) + status_counts.get("completed", 0) + status_counts.get("sequenced", 0)
            }
