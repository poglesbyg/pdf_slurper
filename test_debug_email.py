#!/usr/bin/env python3
"""Debug the EmailAddress issue."""

import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from src.application.container import Container
from src.infrastructure.pdf.processor import PDFProcessor
import asyncio

async def test():
    # First test the processor alone
    processor = PDFProcessor()
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    
    print("📄 Step 1: Testing PDF Processor...")
    result = await processor.process(pdf_path)
    
    email = result.get("metadata", {}).get("requester_email")
    print(f"  Email extracted: {email}")
    print(f"  Email type: {type(email)}")
    print()
    
    # Now test the service
    print("📋 Step 2: Testing Submission Service...")
    container = Container()
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        shutil.copy(pdf_path, tmp.name)
        temp_path = Path(tmp.name)
    
    try:
        # Force creation of new submission
        submission = await container.submission_service.create_from_pdf(
            pdf_path=temp_path,
            storage_location="Debug Test",
            force=True
        )
        
        print(f"  Submission created: {submission.id}")
        if hasattr(submission, 'metadata'):
            print(f"  Email in metadata: {submission.metadata.requester_email}")
            print(f"  Email type: {type(submission.metadata.requester_email)}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        temp_path.unlink()

# Run the test
asyncio.run(test())
