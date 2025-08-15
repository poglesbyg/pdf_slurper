"""Adapter to bridge old and new code during migration."""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Import old code
import sys
sys.path.append(str(Path(__file__).parent.parent))
from pdf_slurper.db import init_db as old_init_db, open_session as old_open_session
from pdf_slurper.slurp import slurp_pdf as old_slurp_pdf

# Import new code
from .application.container import Container
from .infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class MigrationAdapter:
    """Adapter to use new modular code with old system."""
    
    def __init__(self, use_new_code: bool = False):
        """Initialize adapter.
        
        Args:
            use_new_code: Whether to use new modular code
        """
        self.use_new_code = use_new_code
        self.container: Optional[Container] = None
        
        if use_new_code:
            # Initialize new container
            settings = Settings()
            self.container = Container(settings)
            logger.info("Using new modular architecture")
        else:
            logger.info("Using legacy code")
    
    def slurp_pdf(
        self,
        pdf_path: Path,
        db_path: Optional[Path] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Process PDF file.
        
        Args:
            pdf_path: Path to PDF file
            db_path: Database path (for old code)
            force: Force re-import
            
        Returns:
            Processing result
        """
        if self.use_new_code:
            # Use new code
            return self._slurp_pdf_new(pdf_path, force)
        else:
            # Use old code
            return self._slurp_pdf_old(pdf_path, db_path, force)
    
    def _slurp_pdf_old(
        self,
        pdf_path: Path,
        db_path: Optional[Path],
        force: bool
    ) -> Dict[str, Any]:
        """Process PDF using old code."""
        result = old_slurp_pdf(pdf_path, db_path=db_path, force=force)
        return {
            "submission_id": result.submission_id,
            "num_samples": result.num_samples,
            "source": "legacy"
        }
    
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
        """Initialize database.
        
        Args:
            db_path: Database path
        """
        if self.use_new_code:
            # Use new code
            self.container.database.create_tables()
            logger.info("Initialized database (new)")
        else:
            # Use old code
            old_init_db(db_path)
            logger.info("Initialized database (legacy)")
    
    def get_submission_statistics(self, submission_id: str) -> Dict[str, Any]:
        """Get submission statistics.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            Statistics
        """
        if self.use_new_code:
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
        else:
            # Use old code
            from pdf_slurper.db import get_submission_statistics
            with old_open_session() as session:
                return get_submission_statistics(session, submission_id)
    
    def apply_qc(
        self,
        submission_id: str,
        min_concentration: float = 10.0,
        min_volume: float = 20.0,
        min_ratio: float = 1.8
    ) -> Dict[str, Any]:
        """Apply QC to submission.
        
        Args:
            submission_id: Submission ID
            min_concentration: Minimum concentration
            min_volume: Minimum volume
            min_ratio: Minimum quality ratio
            
        Returns:
            QC results
        """
        if self.use_new_code:
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
        else:
            # Use old code
            from pdf_slurper.db import apply_qc_thresholds
            with old_open_session() as session:
                flagged = apply_qc_thresholds(
                    session,
                    submission_id,
                    min_concentration,
                    min_volume,
                    min_ratio
                )
                return {"flagged": flagged, "source": "legacy"}
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.container:
            self.container.close()


# Global adapter instance
_adapter: Optional[MigrationAdapter] = None


def get_adapter(use_new_code: bool = False) -> MigrationAdapter:
    """Get adapter instance.
    
    Args:
        use_new_code: Whether to use new modular code
        
    Returns:
        Adapter instance
    """
    global _adapter
    if _adapter is None or _adapter.use_new_code != use_new_code:
        _adapter = MigrationAdapter(use_new_code)
    return _adapter


def set_use_new_code(enabled: bool) -> None:
    """Set whether to use new modular code.
    
    Args:
        enabled: Whether to use new code
    """
    global _adapter
    _adapter = MigrationAdapter(enabled)
