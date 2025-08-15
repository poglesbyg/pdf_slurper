"""Integration tests for SubmissionRepository."""

import pytest
from datetime import datetime, timedelta

from src.domain.models.value_objects import SubmissionId
from src.infrastructure.persistence.repositories.submission_repository import SQLSubmissionRepository
from src.domain.repositories.base import Pagination


@pytest.mark.asyncio
class TestSubmissionRepository:
    """Test submission repository."""
    
    async def test_save_and_get(self, test_database, sample_submission):
        """Test saving and retrieving submission."""
        repo = SQLSubmissionRepository(test_database)
        
        # Save submission
        saved = await repo.save(sample_submission)
        assert saved.id == sample_submission.id
        
        # Get submission
        retrieved = await repo.get(sample_submission.id)
        assert retrieved is not None
        assert retrieved.id == sample_submission.id
        assert len(retrieved.samples) == len(sample_submission.samples)
    
    async def test_get_nonexistent(self, test_database):
        """Test getting non-existent submission."""
        repo = SQLSubmissionRepository(test_database)
        
        result = await repo.get(SubmissionId("nonexistent"))
        assert result is None
    
    async def test_delete(self, test_database, sample_submission):
        """Test deleting submission."""
        repo = SQLSubmissionRepository(test_database)
        
        # Save submission
        await repo.save(sample_submission)
        
        # Delete submission
        deleted = await repo.delete(sample_submission.id)
        assert deleted is True
        
        # Verify deleted
        result = await repo.get(sample_submission.id)
        assert result is None
    
    async def test_delete_nonexistent(self, test_database):
        """Test deleting non-existent submission."""
        repo = SQLSubmissionRepository(test_database)
        
        deleted = await repo.delete(SubmissionId("nonexistent"))
        assert deleted is False
    
    async def test_exists(self, test_database, sample_submission):
        """Test checking if submission exists."""
        repo = SQLSubmissionRepository(test_database)
        
        # Before saving
        exists = await repo.exists(sample_submission.id)
        assert exists is False
        
        # After saving
        await repo.save(sample_submission)
        exists = await repo.exists(sample_submission.id)
        assert exists is True
    
    async def test_count(self, test_database, sample_submission):
        """Test counting submissions."""
        repo = SQLSubmissionRepository(test_database)
        
        # Initial count
        count = await repo.count()
        assert count == 0
        
        # After saving
        await repo.save(sample_submission)
        count = await repo.count()
        assert count == 1
    
    async def test_get_all_with_pagination(self, test_database):
        """Test getting all submissions with pagination."""
        repo = SQLSubmissionRepository(test_database)
        
        # Create multiple submissions
        for i in range(5):
            submission = await self._create_submission(f"sub_{i}")
            await repo.save(submission)
        
        # Get first page
        page1 = await repo.get_all(Pagination(offset=0, limit=2))
        assert len(page1) == 2
        
        # Get second page
        page2 = await repo.get_all(Pagination(offset=2, limit=2))
        assert len(page2) == 2
        
        # Get third page
        page3 = await repo.get_all(Pagination(offset=4, limit=2))
        assert len(page3) == 1
    
    async def test_find_by_hash(self, test_database, sample_submission):
        """Test finding submission by file hash."""
        repo = SQLSubmissionRepository(test_database)
        
        # Save submission
        await repo.save(sample_submission)
        
        # Find by hash
        found = await repo.find_by_hash(sample_submission.pdf_source.file_hash)
        assert found is not None
        assert found.id == sample_submission.id
        
        # Find non-existent hash
        not_found = await repo.find_by_hash("nonexistent_hash")
        assert not_found is None
    
    async def test_find_by_identifier(self, test_database, sample_submission):
        """Test finding submission by business identifier."""
        repo = SQLSubmissionRepository(test_database)
        
        # Save submission
        await repo.save(sample_submission)
        
        # Find by identifier
        found = await repo.find_by_identifier(sample_submission.metadata.identifier)
        assert found is not None
        assert found.id == sample_submission.id
    
    async def test_find_by_requester_email(self, test_database):
        """Test finding submissions by requester email."""
        repo = SQLSubmissionRepository(test_database)
        
        # Create submissions with different emails
        sub1 = await self._create_submission("sub_1", email="user1@test.com")
        sub2 = await self._create_submission("sub_2", email="user2@test.com")
        sub3 = await self._create_submission("sub_3", email="user1@test.com")
        
        await repo.save(sub1)
        await repo.save(sub2)
        await repo.save(sub3)
        
        # Find by email
        results = await repo.find_by_requester_email("user1@test.com")
        assert len(results) == 2
        assert all(s.metadata.requester_email.value == "user1@test.com" for s in results)
    
    async def test_find_by_date_range(self, test_database):
        """Test finding submissions by date range."""
        repo = SQLSubmissionRepository(test_database)
        
        # Create submissions with different dates
        now = datetime.utcnow()
        
        sub1 = await self._create_submission("sub_1")
        sub1.created_at = now - timedelta(days=5)
        
        sub2 = await self._create_submission("sub_2")
        sub2.created_at = now - timedelta(days=2)
        
        sub3 = await self._create_submission("sub_3")
        sub3.created_at = now
        
        await repo.save(sub1)
        await repo.save(sub2)
        await repo.save(sub3)
        
        # Find in range
        start_date = now - timedelta(days=3)
        end_date = now + timedelta(days=1)
        
        results = await repo.find_by_date_range(start_date, end_date)
        assert len(results) == 2
    
    async def test_find_by_lab(self, test_database):
        """Test finding submissions by lab."""
        repo = SQLSubmissionRepository(test_database)
        
        # Create submissions with different labs
        sub1 = await self._create_submission("sub_1", lab="Lab A")
        sub2 = await self._create_submission("sub_2", lab="Lab B")
        sub3 = await self._create_submission("sub_3", lab="Lab A")
        
        await repo.save(sub1)
        await repo.save(sub2)
        await repo.save(sub3)
        
        # Find by lab
        results = await repo.find_by_lab("Lab A")
        assert len(results) == 2
        assert all("Lab A" in s.metadata.lab for s in results)
    
    async def test_search(self, test_database):
        """Test searching submissions."""
        repo = SQLSubmissionRepository(test_database)
        
        # Create submissions
        sub1 = await self._create_submission("sub_1", identifier="TEST-001")
        sub2 = await self._create_submission("sub_2", identifier="TEST-002")
        sub3 = await self._create_submission("sub_3", identifier="OTHER-001")
        
        await repo.save(sub1)
        await repo.save(sub2)
        await repo.save(sub3)
        
        # Search
        page = await repo.search("TEST")
        assert page.total == 2
        assert len(page.items) == 2
        assert page.has_next is False
    
    async def test_get_statistics(self, test_database, sample_submission):
        """Test getting statistics."""
        repo = SQLSubmissionRepository(test_database)
        
        # Save submission
        await repo.save(sample_submission)
        
        # Get statistics
        stats = await repo.get_statistics()
        
        assert stats["total_submissions"] == 1
        assert stats["total_samples"] == len(sample_submission.samples)
        assert "status_counts" in stats
        assert "qc_status_counts" in stats
    
    async def _create_submission(
        self,
        submission_id: str,
        email: str = "test@test.com",
        lab: str = "Test Lab",
        identifier: str = "TEST-001"
    ):
        """Helper to create submission."""
        from src.domain.models.submission import Submission, SubmissionMetadata, PDFSource
        from src.domain.models.sample import Sample, Measurements
        from src.domain.models.value_objects import EmailAddress
        from pathlib import Path
        
        metadata = SubmissionMetadata(
            identifier=identifier,
            service_requested="Test Service",
            requester="Test User",
            requester_email=EmailAddress(email),
            lab=lab
        )
        
        pdf_source = PDFSource(
            file_path=Path(f"/tmp/{submission_id}.pdf"),
            file_hash=f"hash_{submission_id}",
            file_size=1000,
            modification_time=datetime.utcnow(),
            page_count=5
        )
        
        samples = [
            Sample(
                id=SampleId(f"sample_{submission_id}_{i}"),
                submission_id=submission_id,
                name=f"Sample {i}",
                measurements=Measurements()
            )
            for i in range(2)
        ]
        
        return Submission(
            id=SubmissionId(submission_id),
            samples=samples,
            metadata=metadata,
            pdf_source=pdf_source
        )
