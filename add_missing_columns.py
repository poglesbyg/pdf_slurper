#!/usr/bin/env python3
"""Add missing columns to the submission_v2 table."""

import sqlite3
from pathlib import Path

# Connect to the database
db_path = Path("slurper.db")
if not db_path.exists():
    print("❌ Database not found at slurper.db")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing columns
cursor.execute("PRAGMA table_info(submission_v2)")
existing_columns = {row[1] for row in cursor.fetchall()}
print(f"Existing columns in submission_v2: {len(existing_columns)}")

# Define columns to add
columns_to_add = [
    ("will_submit_dna_for", "TEXT"),
    ("type_of_sample", "TEXT"),
    ("sample_buffer", "TEXT"),
    ("notes", "TEXT"),
]

# Add missing columns
added = 0
for column_name, column_type in columns_to_add:
    if column_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE submission_v2 ADD COLUMN {column_name} {column_type}")
            print(f"✅ Added column: {column_name}")
            added += 1
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"❌ Error adding {column_name}: {e}")
    else:
        print(f"  Column {column_name} already exists")

# Commit changes
conn.commit()

print(f"\n📊 Added {added} new columns to submission_v2")

# Verify the columns were added
cursor.execute("PRAGMA table_info(submission_v2)")
all_columns = [row[1] for row in cursor.fetchall()]
print(f"Total columns now: {len(all_columns)}")

# Check if all required fields are present
required_fields = [
    'identifier', 'as_of', 'expires_on', 'service_requested',
    'requester', 'requester_email', 'phone', 'lab',
    'billing_address', 'pis', 'financial_contacts',
    'request_summary', 'forms_text', 'will_submit_dna_for',
    'type_of_sample', 'human_dna', 'source_organism',
    'sample_buffer', 'notes'
]

missing = [f for f in required_fields if f not in all_columns and f"{f}_json" not in all_columns]
if missing:
    print(f"\n⚠️ Still missing: {', '.join(missing)}")
else:
    print("\n✅ All required fields are present!")

conn.close()
print("\nDatabase updated successfully!")
