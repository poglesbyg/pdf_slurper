#!/usr/bin/env python3
"""Find the exact line causing the error."""

import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from src.application.container import Container
from src.presentation.api.v1.schemas.submission import SubmissionResponse, SubmissionMetadataResponse
import asyncio

async def test():
    container = Container()
    
    # Create a temp copy
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        shutil.copy(pdf_path, tmp.name)
        temp_path = Path(tmp.name)
    
    try:
        # Create submission
        print("1. Creating submission...")
        submission = await container.submission_service.create_from_pdf(
            pdf_path=temp_path,
            storage_location="Test",
            force=True
        )
        print(f"   ✓ Created: {submission.id}")
        
        # Try to build the response like the API does
        print("\n2. Building API response...")
        
        print("   Checking metadata fields:")
        print(f"   - identifier: {submission.metadata.identifier}")
        print(f"   - requester: {submission.metadata.requester}")
        print(f"   - requester_email: {submission.metadata.requester_email}")
        print(f"   - requester_email type: {type(submission.metadata.requester_email)}")
        
        # Try extracting email value
        print("\n3. Extracting email value...")
        try:
            email_value = submission.metadata.requester_email.value if submission.metadata.requester_email else None
            print(f"   ✓ Email value: {email_value}")
        except AttributeError as e:
            print(f"   ✗ Error extracting email: {e}")
            print(f"   Email object: {submission.metadata.requester_email}")
            print(f"   Dir of email: {dir(submission.metadata.requester_email)[:200]}")
        
        # Try extracting organism
        print("\n4. Extracting organism...")
        try:
            organism_value = submission.metadata.organism.species if submission.metadata.organism else None
            print(f"   ✓ Organism value: {organism_value}")
        except AttributeError as e:
            print(f"   ✗ Error extracting organism: {e}")
            
        # Try building full response
        print("\n5. Building full response...")
        try:
            response = SubmissionResponse(
                id=submission.id,
                created_at=submission.created_at,
                updated_at=submission.created_at,
                sample_count=len(submission.samples) if hasattr(submission, 'samples') else 0,
                metadata=SubmissionMetadataResponse(
                    identifier=submission.metadata.identifier,
                    service_requested=submission.metadata.service_requested,
                    requester=submission.metadata.requester,
                    requester_email=email_value,
                    lab=submission.metadata.lab,
                    organism=organism_value,
                    contains_human_dna=submission.metadata.contains_human_dna,
                    storage_location=submission.metadata.storage_location,
                    source_organism=submission.metadata.source_organism,
                    sample_buffer=submission.metadata.sample_buffer,
                    will_submit_dna_for=submission.metadata.will_submit_dna_for,
                    type_of_sample=submission.metadata.type_of_sample
                )
            )
            print(f"   ✓ Response built successfully!")
            print(f"   Response ID: {response.id}")
            print(f"   Response metadata email: {response.metadata.requester_email}")
        except Exception as e:
            print(f"   ✗ Error building response: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        temp_path.unlink()

# Run
asyncio.run(test())
