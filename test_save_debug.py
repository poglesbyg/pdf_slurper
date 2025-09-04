#!/usr/bin/env python3
"""Debug the saving process."""

import asyncio
from pathlib import Path
import sys
import uuid
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.application.services.submission_service import SubmissionService
from src.application.container import Container
from src.infrastructure.pdf.processor import PDFProcessor
from src.domain.models.value_objects import SubmissionId

async def test():
    # Create container
    container = Container()
    service = SubmissionService(
        repository=container.submission_repository,
        pdf_processor=PDFProcessor()
    )
    
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    
    print("📄 Processing PDF and creating submission...")
    
    # Create submission from PDF
    submission = await service.create_from_pdf(
        pdf_path=pdf_path,
        storage_location="Debug Test",
        force=True
    )
    
    print(f"✅ Created submission: {submission.id}")
    print(f"📦 Samples in domain model: {len(submission.samples)}")
    
    if submission.samples:
        print("\nFirst 5 samples in domain model:")
        for i, sample in enumerate(submission.samples[:5], 1):
            m = sample.measurements
            print(f"  {i}. {sample.name}:")
            print(f"     - Volume: {m.volume.value if m.volume else 0} µL")
            print(f"     - Nanodrop: {m.nanodrop_concentration.value if m.nanodrop_concentration else 0} ng/µL")
            print(f"     - Qubit: {m.qubit_concentration.value if m.qubit_concentration else 0} ng/µL")
    
    # Now check what was saved to database
    print("\n" + "="*60)
    print("Checking database...")
    
    from sqlmodel import Session, select
    from src.infrastructure.persistence.models import SampleORM
    
    with Session(container.database.engine) as session:
        stmt = (
            select(SampleORM)
            .where(SampleORM.submission_id == str(submission.id))
            .limit(5)
        )
        
        db_samples = session.exec(stmt).all()
        
        print(f"📦 Samples in database: {len(db_samples)}")
        
        if db_samples:
            print("\nFirst 5 samples in database:")
            for i, sample in enumerate(db_samples, 1):
                print(f"  {i}. {sample.name}:")
                print(f"     - Volume: {sample.volume_ul} µL")
                print(f"     - Nanodrop: {sample.nanodrop_ng_per_ul} ng/µL")
                print(f"     - Qubit: {sample.qubit_ng_per_ul} ng/µL")

asyncio.run(test())
