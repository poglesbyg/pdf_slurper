#!/usr/bin/env python3
"""Fix database location and ensure all tables have correct schema."""

from sqlmodel import SQLModel, create_engine
from pathlib import Path
import sys

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the models
from src.infrastructure.persistence.models import SubmissionORM, SampleORM

# Create engine for the CORRECT database location
db_path = Path("data/pdf_slurper.db")
db_path.parent.mkdir(exist_ok=True)

print(f"🔧 Setting up database at: {db_path}")

engine = create_engine(f"sqlite:///{db_path}", echo=False)

# Drop old v2 tables if they exist (to recreate with all columns)
import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='submission_v2'")
existing_schema = cursor.fetchone()
if existing_schema:
    # Count columns
    cursor.execute("PRAGMA table_info(submission_v2)")
    columns = cursor.fetchall()
    print(f"   Current submission_v2 has {len(columns)} columns")
    
    # Check for new fields
    column_names = [col[1] for col in columns]
    new_fields = ['will_submit_dna_for', 'type_of_sample', 'sample_buffer', 'notes']
    missing = [f for f in new_fields if f not in column_names]
    
    if missing:
        print(f"   Missing fields: {', '.join(missing)}")
        print("   Dropping and recreating tables...")
        cursor.execute("DROP TABLE IF EXISTS sample_v2")
        cursor.execute("DROP TABLE IF EXISTS submission_v2")
        conn.commit()

conn.close()

# Create all tables with correct schema
print("📋 Creating tables with complete schema...")
try:
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully!")
    
    # Verify the tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(submission_v2)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    print(f"\n✅ submission_v2 table has {len(columns)} columns")
    
    # Check key fields
    key_fields = ['identifier', 'requester', 'as_of', 'will_submit_dna_for', 
                  'type_of_sample', 'sample_buffer', 'notes']
    present = [f for f in key_fields if f in column_names]
    print(f"   Key fields present: {', '.join(present)}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✨ Database ready at data/pdf_slurper.db with all fields!")
