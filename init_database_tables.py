#!/usr/bin/env python3
"""Initialize the database tables for v2 models."""

from sqlmodel import SQLModel, create_engine
from pathlib import Path
import sys

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the models
from src.infrastructure.persistence.models import SubmissionORM, SampleORM

# Create engine
db_path = Path("slurper.db")
engine = create_engine(f"sqlite:///{db_path}", echo=True)

print("🔧 Creating database tables...")

# Create all tables
try:
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully!")
    
    # List created tables
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\n📋 Created tables:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n  {table_name}: {len(columns)} columns")
        
        # Show some key columns for submission_v2
        if table_name == "submission_v2":
            column_names = [col[1] for col in columns]
            key_fields = ['identifier', 'requester', 'service_requested', 'as_of', 
                          'will_submit_dna_for', 'type_of_sample', 'notes']
            present = [f for f in key_fields if f in column_names]
            print(f"    Key fields present: {', '.join(present)}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    import traceback
    traceback.print_exc()
