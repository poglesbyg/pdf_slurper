#!/usr/bin/env python3
"""Add the new flow cell and bioinformatics columns to database."""

from sqlmodel import SQLModel, create_engine
from pathlib import Path
import sys
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))

# Import the models
from src.infrastructure.persistence.models import SubmissionORM, SampleORM

# Database path
db_path = Path("data/pdf_slurper.db")

print(f"📋 Adding new columns to database at: {db_path}")

# Check current schema
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if new columns exist
cursor.execute("PRAGMA table_info(submission_v2)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

new_fields = [
    'flow_cell_type', 'genome_size', 'coverage_needed', 'flow_cells_count',
    'basecalling', 'file_format', 'data_delivery'
]

missing = [f for f in new_fields if f not in column_names]

if missing:
    print(f"  Missing fields: {', '.join(missing)}")
    print("  Adding new columns...")
    
    # Add each missing column
    for field in missing:
        try:
            cursor.execute(f"ALTER TABLE submission_v2 ADD COLUMN {field} TEXT")
            print(f"    ✓ Added {field}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"    - {field} already exists")
            else:
                print(f"    ✗ Error adding {field}: {e}")
    
    conn.commit()
    print("  ✅ All columns added successfully!")
else:
    print("  ✅ All columns already exist!")

conn.close()

print("\n🔄 Database updated with all HTSF fields!")
