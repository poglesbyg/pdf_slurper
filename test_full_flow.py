#!/usr/bin/env python3
"""Test the full upload flow to see where fields are lost."""

import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from src.application.container import Container
import asyncio

async def test():
    container = Container()
    
    # Create a temp copy of the PDF
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        shutil.copy(pdf_path, tmp.name)
        temp_path = Path(tmp.name)
    
    print("📄 Testing full submission creation flow...")
    print("="*60)
    
    try:
        # Create submission through the service
        submission = await container.submission_service.create_from_pdf(
            pdf_path=temp_path,
            storage_location="Test Location"
        )
        
        print("\n✅ Submission created!")
        print(f"  ID: {submission.id}")
        print(f"  Samples: {len(submission.samples) if hasattr(submission, 'samples') else 'N/A'}")
        
        print("\n📋 Metadata fields:")
        if hasattr(submission, 'metadata'):
            metadata = submission.metadata
            attrs = ['identifier', 'service_requested', 'requester', 'requester_email', 
                     'lab', 'will_submit_dna_for', 'type_of_sample', 'human_dna', 
                     'source_organism', 'sample_buffer', 'storage_location']
            
            for attr in attrs:
                value = getattr(metadata, attr, None)
                if value:
                    value_str = str(value)[:60] if len(str(value)) > 60 else str(value)
                    print(f"  ✓ {attr}: {value_str}")
                else:
                    print(f"  ✗ {attr}: None")
        else:
            print("  No metadata attribute")
            
    finally:
        # Clean up
        temp_path.unlink()

# Run the test
asyncio.run(test())
