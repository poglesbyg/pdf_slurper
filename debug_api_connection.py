#!/usr/bin/env python3
"""Debug the API database connection issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select, func, create_engine
from src.infrastructure.persistence.models import SampleORM
from src.infrastructure.config.settings import get_settings
from src.application.container import Container

# Test 1: Direct database connection
print("=" * 60)
print("TEST 1: Direct SQLite Connection")
print("-" * 60)

import sqlite3
conn = sqlite3.connect("data/pdf_slurper.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM sample_v2")
direct_count = cursor.fetchone()[0]
print(f"Direct SQLite count: {direct_count}")

cursor.execute("SELECT submission_id, COUNT(*) as cnt FROM sample_v2 GROUP BY submission_id LIMIT 3")
for row in cursor.fetchall():
    print(f"  Submission {row[0][:8]}...: {row[1]} samples")
conn.close()

# Test 2: Using Settings
print("\n" + "=" * 60)
print("TEST 2: Using Settings Database URL")
print("-" * 60)

settings = get_settings()
print(f"Database URL: {settings.database_url}")
print(f"Data Dir: {settings.data_dir}")

engine = create_engine(settings.database_url)
with Session(engine) as session:
    count = session.exec(select(func.count()).select_from(SampleORM)).one()
    print(f"Count via settings engine: {count}")

# Test 3: Using Container (like API does)
print("\n" + "=" * 60)
print("TEST 3: Using Container (API Method)")
print("-" * 60)

container = Container()
print(f"Container database URL: {container.database.database_url}")

with Session(container.database.engine) as session:
    count = session.exec(select(func.count()).select_from(SampleORM)).one()
    print(f"Count via container: {count}")
    
    # Test specific submission
    test_id = "97c30e3a-9c8b-44fd-85ad-5dc1fcaa4029"
    specific_count = session.exec(
        select(func.count()).select_from(SampleORM).where(
            SampleORM.submission_id == test_id
        )
    ).one()
    print(f"Samples for {test_id}: {specific_count}")
    
    # Get actual samples
    samples = session.exec(
        select(SampleORM).where(
            SampleORM.submission_id == test_id
        ).limit(3)
    ).all()
    
    print(f"Retrieved {len(samples)} sample objects")
    for s in samples:
        print(f"  - {s.name}: vol={s.volume_ul}, nano={s.nanodrop_ng_per_ul}")

# Test 4: Check if it's a different database file
print("\n" + "=" * 60)
print("TEST 4: Database File Paths")
print("-" * 60)

import os
print(f"Current working directory: {os.getcwd()}")
print(f"data/pdf_slurper.db exists: {os.path.exists('data/pdf_slurper.db')}")
print(f"data/pdf_slurper.db size: {os.path.getsize('data/pdf_slurper.db')} bytes")

# Check if there are multiple database files
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.db'):
            path = os.path.join(root, file)
            size = os.path.getsize(path)
            print(f"Found DB: {path} ({size} bytes)")
