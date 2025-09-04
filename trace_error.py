#!/usr/bin/env python3
"""Trace the exact error location."""

import sys
from pathlib import Path
import tempfile
import shutil
import traceback

sys.path.insert(0, str(Path(__file__).parent))

from src.application.container import Container
import asyncio

async def test():
    container = Container()
    
    # Create a temp copy
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        shutil.copy(pdf_path, tmp.name)
        temp_path = Path(tmp.name)
    
    try:
        # Force creation with detailed error catching
        print("Creating submission...")
        submission = await container.submission_service.create_from_pdf(
            pdf_path=temp_path,
            storage_location="Debug Test",
            force=True
        )
        
        print(f"✅ Created: {submission.id}")
        
        # Now try to save it to repository
        print("Saving to repository...")
        saved = await container.submission_repository.save(submission)
        print(f"✅ Saved: {saved.id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n📍 Full Traceback:")
        traceback.print_exc()
    finally:
        temp_path.unlink()

# Run
asyncio.run(test())
