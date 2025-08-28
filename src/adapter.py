"""Adapter to bridge old and new code during migration."""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Import new code only - removed legacy imports
from .application.container import Container
from .infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class MigrationAdapter:
    """Adapter to use only new modular code - legacy support removed."""
    
    def __init__(self):
        """Initialize adapter with new modular code only."""
        # Always use new code now
        settings = Settings()
        self.container = Container(settings)
        logger.info("Using new modular architecture")
    
    def slurp_pdf(
        self,
        pdf_path: Path,
        db_path: Optional[Path] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Process PDF file using new modular code.
        
        Args:
            pdf_path: Path to PDF file
            db_path: Database path (ignored, for backwards compatibility)
            force: Force re-import
            
        Returns:
            Processing result
        """
        return self._slurp_pdf_new(pdf_path, force)
    
    def _slurp_pdf_new(self, pdf_path: Path, force: bool) -> Dict[str, Any]:
        """Process PDF using new code."""
        # Run async code in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            submission = loop.run_until_complete(
                self.container.submission_service.create_from_pdf(pdf_path, force)
            )
            return {
                "submission_id": submission.id,
                "num_samples": submission.sample_count,
                "source": "modular"
            }
        finally:
            loop.close()
    
    def init_database(self, db_path: Optional[Path] = None) -> None:
        """Initialize database using new modular code.
        
        Args:
            db_path: Database path (ignored, for backwards compatibility)
        """
        # Use new code
        self.container.database.create_tables()
        logger.info("Initialized database (new)")
    
    def get_submission_statistics(self, submission_id: str) -> Dict[str, Any]:
        """Get submission statistics using new modular code.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            Statistics
        """
        # Use new code
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from .domain.models.value_objects import SubmissionId
            stats = loop.run_until_complete(
                self.container.submission_service.get_statistics(
                    SubmissionId(submission_id)
                )
            )
            return stats
        finally:
            loop.close()
    
    def apply_qc(
        self,
        submission_id: str,
        min_concentration: float = 10.0,
        min_volume: float = 20.0,
        min_ratio: float = 1.8
    ) -> Dict[str, Any]:
        """Apply QC to submission using new modular code.
        
        Args:
            submission_id: Submission ID
            min_concentration: Minimum concentration
            min_volume: Minimum volume
            min_ratio: Minimum quality ratio
            
        Returns:
            QC results
        """
        # Use new code
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from .domain.models.value_objects import SubmissionId
            results = loop.run_until_complete(
                self.container.submission_service.apply_qc(
                    SubmissionId(submission_id),
                    min_concentration=min_concentration,
                    min_volume=min_volume,
                    min_quality_ratio=min_ratio
                )
            )
            return results
        finally:
            loop.close()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.container:
            self.container.close()


# Global adapter instance
_adapter: Optional[MigrationAdapter] = None


def get_adapter() -> MigrationAdapter:
    """Get adapter instance using new modular code.
        
    Returns:
        Adapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = MigrationAdapter()
    return _adapter


def set_use_new_code(enabled: bool) -> None:
    """No longer needed - always uses new modular code.
    
    Args:
        enabled: Ignored, kept for backwards compatibility
    """
    pass  # Always uses new code now
