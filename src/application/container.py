"""Dependency injection container."""

from typing import Optional
from functools import lru_cache
import logging

from ..infrastructure.config.settings import Settings, get_settings
from ..infrastructure.persistence.database import Database
from ..domain.repositories.submission_repository import SubmissionRepository


logger = logging.getLogger(__name__)


class Container:
    """Application dependency container."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize container.
        
        Args:
            settings: Application settings (uses default if None)
        """
        self._settings = settings or get_settings()
        self._database: Optional[Database] = None
        self._submission_repository: Optional[SubmissionRepository] = None
        self._submission_service: Optional['SubmissionService'] = None
        self._pdf_processor: Optional['PDFProcessor'] = None
    
    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings
    
    @property
    def database(self) -> 'Database':
        """Get database instance."""
        if self._database is None:
            from ..infrastructure.persistence.database import Database
            self._database = Database(self._settings.database_url)
            logger.info(f"Initialized database: {self._settings.database_url}")
        return self._database
    
    @property
    def submission_repository(self) -> SubmissionRepository:
        """Get submission repository."""
        if self._submission_repository is None:
            from ..infrastructure.persistence.repositories.submission_repository import (
                SQLSubmissionRepository
            )
            self._submission_repository = SQLSubmissionRepository(self.database)
            logger.info("Initialized submission repository")
        return self._submission_repository
    
    @property
    def pdf_processor(self) -> 'PDFProcessor':
        """Get PDF processor."""
        if self._pdf_processor is None:
            from ..infrastructure.pdf.processor import PDFProcessor
            self._pdf_processor = PDFProcessor()
            logger.info("Initialized PDF processor")
        return self._pdf_processor
    
    @property
    def submission_service(self) -> 'SubmissionService':
        """Get submission service."""
        if self._submission_service is None:
            from .services.submission_service import SubmissionService
            self._submission_service = SubmissionService(
                repository=self.submission_repository,
                pdf_processor=self.pdf_processor,
                qc_auto_apply=self._settings.qc_auto_apply
            )
            logger.info("Initialized submission service")
        return self._submission_service
    
    @property
    def sample_service(self) -> 'SampleService':
        """Get sample service."""
        # Implement similarly to submission_service
        raise NotImplementedError
    
    def close(self) -> None:
        """Close all resources."""
        if self._database:
            self._database.close()
            logger.info("Closed database connection")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get global container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def init_container(settings: Optional[Settings] = None) -> Container:
    """Initialize global container.
    
    Args:
        settings: Application settings
        
    Returns:
        Container instance
    """
    global _container
    _container = Container(settings)
    return _container


def close_container() -> None:
    """Close global container."""
    global _container
    if _container:
        _container.close()
        _container = None


# FastAPI dependency
async def get_container_dependency() -> Container:
    """Get container for FastAPI dependency injection."""
    return get_container()
