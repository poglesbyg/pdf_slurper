#!/usr/bin/env python3
"""Test the samples API directly."""

from sqlmodel import Session, select, func
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.persistence.models import SampleORM
from src.infrastructure.persistence.database import Database
from src.infrastructure.config.settings import get_settings

submission_id = "97c30e3a-9c8b-44fd-85ad-5dc1fcaa4029"

print(f"Testing samples for submission: {submission_id}")
print("="*60)

settings = get_settings()
database = Database(settings.database_url)

with Session(database.engine) as session:
    # Count samples
    count_stmt = select(func.count(SampleORM.id)).where(
        SampleORM.submission_id == submission_id
    )
    total = session.exec(count_stmt).one()
    
    print(f"Total samples in database: {total}")
    
    # Get samples
    stmt = (
        select(SampleORM)
        .where(SampleORM.submission_id == submission_id)
        .limit(5)
    )
    
    samples = session.exec(stmt).all()
    
    print(f"Samples retrieved: {len(samples)}")
    
    if samples:
        print("\nFirst 5 samples:")
        for i, sample in enumerate(samples, 1):
            print(f"  {i}. {sample.name}: Vol={sample.volume_ul} Nano={sample.nanodrop_ng_per_ul}")
    
    # Check all submission IDs in the database
    print("\n" + "-"*60)
    print("All unique submission_ids in sample_v2:")
    all_subs = session.exec(
        select(SampleORM.submission_id).distinct().limit(10)
    ).all()
    
    for sub in all_subs[:5]:
        count = session.exec(
            select(func.count(SampleORM.id)).where(
                SampleORM.submission_id == sub
            )
        ).one()
        print(f"  {sub}: {count} samples")
