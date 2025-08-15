"""Submission repository interface."""

from abc import abstractmethod
from typing import Optional, List
from datetime import datetime

from .base import Repository, Page, Pagination
from ..models.submission import Submission
from ..models.value_objects import SubmissionId


class SubmissionRepository(Repository[Submission, SubmissionId]):
    """Repository interface for Submission entities."""
    
    @abstractmethod
    async def find_by_hash(self, file_hash: str) -> Optional[Submission]:
        """Find submission by PDF file hash."""
        pass
    
    @abstractmethod
    async def find_by_identifier(self, identifier: str) -> Optional[Submission]:
        """Find submission by business identifier."""
        pass
    
    @abstractmethod
    async def find_by_requester_email(
        self,
        email: str,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions by requester email."""
        pass
    
    @abstractmethod
    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions within date range."""
        pass
    
    @abstractmethod
    async def find_by_lab(
        self,
        lab: str,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions by lab."""
        pass
    
    @abstractmethod
    async def find_with_samples_needing_qc(
        self,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find submissions with samples that need QC."""
        pass
    
    @abstractmethod
    async def find_expired(
        self,
        pagination: Optional[Pagination] = None
    ) -> List[Submission]:
        """Find expired submissions."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        pagination: Optional[Pagination] = None
    ) -> Page[Submission]:
        """Search submissions by text query."""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> dict:
        """Get global statistics across all submissions."""
        pass
