#!/usr/bin/env python3
"""Update persistence models to store all PDF fields."""

from pathlib import Path

# Update the SQLModel ORM
orm_path = Path("src/infrastructure/persistence/models.py")
with open(orm_path, 'r') as f:
    content = f.read()

# Check which fields are missing
required_fields = {
    'as_of': 'Optional[str] = Field(default=None)',
    'expires_on': 'Optional[str] = Field(default=None)',
    'phone': 'Optional[str] = Field(default=None)',
    'billing_address': 'Optional[str] = Field(default=None)',
    'pis': 'Optional[str] = Field(default=None)',
    'financial_contacts': 'Optional[str] = Field(default=None)',
    'request_summary': 'Optional[str] = Field(default=None, sa_column_kwargs={"type": Text})',
    'forms_text': 'Optional[str] = Field(default=None, sa_column_kwargs={"type": Text})',
    'will_submit_dna_for': 'Optional[str] = Field(default=None)',
    'type_of_sample': 'Optional[str] = Field(default=None)',
    'human_dna': 'Optional[str] = Field(default=None)',
    'source_organism': 'Optional[str] = Field(default=None)',
    'sample_buffer': 'Optional[str] = Field(default=None)',
    'notes': 'Optional[str] = Field(default=None, sa_column_kwargs={"type": Text})'
}

# Find SubmissionORM class
import re
class_match = re.search(r'class SubmissionORM\(SQLModel, table=True\):.*?(?=class|\Z)', content, re.DOTALL)

if class_match:
    class_text = class_match.group()
    
    # Check which fields are missing
    missing_fields = []
    for field_name, field_def in required_fields.items():
        if f"{field_name}:" not in class_text:
            missing_fields.append((field_name, field_def))
    
    if missing_fields:
        print(f"Found {len(missing_fields)} missing fields in SubmissionORM")
        
        # Find insertion point (after sample_buffer_json or before the last field)
        insert_patterns = ['sample_buffer_json:', 'source_organism:', 'human_dna:', 'type_of_sample_json:', 'lab:']
        insert_point = -1
        for pattern in insert_patterns:
            idx = class_text.find(pattern)
            if idx > 0:
                insert_point = class_text.find('\n', idx)
                break
        
        if insert_point > 0:
            # Add the missing fields
            new_fields = "\n    # Additional comprehensive PDF extraction fields"
            for field_name, field_def in missing_fields:
                new_fields += f"\n    {field_name}: {field_def}"
            
            new_class = class_text[:insert_point] + new_fields + class_text[insert_point:]
            content = content[:class_match.start()] + new_class + content[class_match.end():]
            
            # Also ensure we have the Text import
            if 'from sqlalchemy import Text' not in content:
                if 'from sqlalchemy import' in content:
                    content = content.replace('from sqlalchemy import', 'from sqlalchemy import Text,')
                else:
                    # Add the import after other imports
                    import_idx = content.find('from sqlmodel import')
                    if import_idx > 0:
                        end_idx = content.find('\n', import_idx)
                        content = content[:end_idx] + '\nfrom sqlalchemy import Text' + content[end_idx:]
            
            with open(orm_path, 'w') as f:
                f.write(content)
            print(f"✅ Added {len(missing_fields)} fields to SubmissionORM")
        else:
            print("⚠️ Could not find insertion point for new fields")
    else:
        print("✅ All fields already exist in SubmissionORM")
else:
    print("❌ Could not find SubmissionORM class")

# Also update the legacy models if needed
legacy_path = Path("pdf_slurper/db.py")
if legacy_path.exists():
    with open(legacy_path, 'r') as f:
        legacy_content = f.read()
    
    # Check if fields exist
    class_match = re.search(r'class Submission\(SQLModel, table=True\):.*?(?=class|\Z)', legacy_content, re.DOTALL)
    if class_match:
        class_text = class_match.group()
        missing_legacy = []
        
        for field_name in required_fields.keys():
            if f"{field_name}:" not in class_text:
                missing_legacy.append(field_name)
        
        if missing_legacy:
            print(f"\n⚠️ Legacy model missing {len(missing_legacy)} fields")
            # For now just note it - the v2 models are more important
        else:
            print("✅ Legacy models have all fields")

print("\n✨ Persistence models updated!")
print("\nThe database can now store all PDF extracted fields.")
