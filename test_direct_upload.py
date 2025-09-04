#!/usr/bin/env python3
"""Direct test of the upload functionality."""

import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

# Test database connection first
from src.infrastructure.config.settings import Settings
from sqlmodel import create_engine, Session, select

settings = Settings()
print(f"Database URL: {settings.database_url}")

# Test write access
try:
    engine = create_engine(settings.database_url, echo=False)
    with Session(engine) as session:
        # Try a simple query
        session.exec(select(1))
        print("✅ Database read successful")
        
        # Try to check if submission_v2 table exists
        from src.infrastructure.persistence.models import SubmissionORM
        count = session.query(SubmissionORM).count()
        print(f"✅ Found {count} submissions in database")
        
except Exception as e:
    print(f"❌ Database error: {e}")
    import traceback
    traceback.print_exc()

# Now test the actual service
print("\nTesting submission service...")
try:
    from src.application.container import Container
    container = Container()
    
    # Test with a simple PDF
    test_pdf = Path("HTSF--JL-147_quote_160217072025.pdf")
    if test_pdf.exists():
        print(f"Using PDF: {test_pdf}")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(test_pdf.read_bytes())
            tmp_path = Path(tmp.name)
        
        # Try to create submission
        import asyncio
        async def test():
            submission = await container.submission_service.create_from_pdf(
                pdf_path=tmp_path,
                storage_location="Test Location"
            )
            return submission
        
        result = asyncio.run(test())
        print(f"✅ Submission created: {result.id}")
        
        # Clean up
        tmp_path.unlink()
    else:
        print("Test PDF not found")
        
except Exception as e:
    print(f"❌ Service error: {e}")
    import traceback
    traceback.print_exc()
