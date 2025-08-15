"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Generator

from src.domain.models.submission import Submission, SubmissionMetadata, PDFSource
from src.domain.models.sample import Sample, Measurements
from src.domain.models.value_objects import (
    SubmissionId, SampleId, Concentration, Volume, QualityRatio
)
from src.infrastructure.persistence.database import Database
from src.infrastructure.config.settings import Settings
from src.application.container import Container


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="testing",
        database_url="sqlite:///:memory:",
        debug=True,
        qc_auto_apply=False
    )


@pytest.fixture
def test_database(test_settings) -> Generator[Database, None, None]:
    """Create test database."""
    db = Database(test_settings.database_url)
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def test_container(test_settings) -> Generator[Container, None, None]:
    """Create test container."""
    container = Container(test_settings)
    yield container
    container.close()


@pytest.fixture
def sample_submission() -> Submission:
    """Create sample submission for testing."""
    metadata = SubmissionMetadata(
        identifier="TEST-001",
        service_requested="Test Service",
        requester="Test User",
        lab="Test Lab"
    )
    
    pdf_source = PDFSource(
        file_path=Path("/tmp/test.pdf"),
        file_hash="abc123",
        file_size=1000,
        modification_time=datetime.utcnow(),
        page_count=5
    )
    
    samples = [
        Sample(
            id=SampleId(f"sample_{i}"),
            submission_id="sub_test",
            name=f"Sample {i}",
            measurements=Measurements(
                volume=Volume(50.0),
                qubit_concentration=Concentration(100.0),
                a260_a280=QualityRatio(1.85)
            )
        )
        for i in range(1, 4)
    ]
    
    return Submission(
        id=SubmissionId("sub_test"),
        samples=samples,
        metadata=metadata,
        pdf_source=pdf_source
    )


@pytest.fixture
def sample_pdf_path() -> Path:
    """Get path to sample PDF file."""
    # Use the existing test PDF
    pdf_path = Path(__file__).parent.parent / "HTSF--JL-147_quote_160217072025.pdf"
    if pdf_path.exists():
        return pdf_path
    
    # Create a dummy file for testing if not exists
    pdf_path = Path("/tmp/test_sample.pdf")
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    return pdf_path
