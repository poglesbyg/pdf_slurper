#!/usr/bin/env python3
"""Debug why samples aren't loading."""

from sqlmodel import Session, select
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.persistence.models import SampleORM
from src.infrastructure.persistence.database import get_engine

submission_id = "cace4c33-9c25-40af-892e-8af25cac197b"

print(f"Looking for samples for submission: {submission_id}")

engine = get_engine()
with Session(engine) as session:
    # Try the exact query from the API
    stmt = (
        select(SampleORM)
        .where(SampleORM.submission_id == submission_id)
        .limit(10)
    )
    
    samples = session.exec(stmt).all()
    
    print(f"Found {len(samples)} samples")
    
    if samples:
        for i, sample in enumerate(samples[:3], 1):
            print(f"\nSample {i}:")
            print(f"  ID: {sample.id}")
            print(f"  Name: {sample.name}")
            print(f"  Volume: {sample.volume_ul}")
    else:
        # Check if there are ANY samples in v2 table
        all_samples = session.exec(select(SampleORM).limit(5)).all()
        print(f"\nTotal samples in sample_v2 table: {len(all_samples)}")
        
        if all_samples:
            print("\nSample submission_ids in database:")
            for s in all_samples:
                print(f"  - {s.submission_id}")
