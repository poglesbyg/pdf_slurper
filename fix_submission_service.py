#!/usr/bin/env python3
"""Fix submission service to use all extracted PDF fields."""

from pathlib import Path

# Read the current service file
service_path = Path("src/application/services/submission_service.py")
with open(service_path, 'r') as f:
    content = f.read()

# Find and replace the limited metadata creation
old_metadata = '''        pdf_metadata = pdf_data.get("metadata", {})
        metadata = SubmissionMetadata(
            identifier=pdf_metadata.get("identifier", ""),
            service_requested=pdf_metadata.get("service_requested", ""),
            requester=pdf_metadata.get("requester", ""),
            requester_email=pdf_metadata.get("requester_email"),
            lab=pdf_metadata.get("lab", ""),
            organism=Organism(
                full_name=pdf_metadata.get("organism")
            ) if pdf_metadata.get("organism") else None,
            contains_human_dna=pdf_metadata.get("contains_human_dna"),
            storage_location=storage_location
        )'''

new_metadata = '''        pdf_metadata = pdf_data.get("metadata", {})
        
        # Create comprehensive metadata from all extracted fields
        metadata = SubmissionMetadata(
            identifier=pdf_metadata.get("identifier", ""),
            service_requested=pdf_metadata.get("service_requested", ""),
            requester=pdf_metadata.get("requester", ""),
            requester_email=pdf_metadata.get("requester_email"),
            lab=pdf_metadata.get("lab", ""),
            organism=Organism(
                full_name=pdf_metadata.get("source_organism") or pdf_metadata.get("organism")
            ) if (pdf_metadata.get("source_organism") or pdf_metadata.get("organism")) else None,
            contains_human_dna=pdf_metadata.get("contains_human_dna"),
            storage_location=storage_location,
            # Additional comprehensive fields
            as_of=pdf_metadata.get("as_of"),
            expires_on=pdf_metadata.get("expires_on"),
            phone=pdf_metadata.get("phone"),
            billing_address=pdf_metadata.get("billing_address"),
            pis=pdf_metadata.get("pis"),
            financial_contacts=pdf_metadata.get("financial_contacts"),
            request_summary=pdf_metadata.get("request_summary"),
            forms_text=pdf_metadata.get("forms_text"),
            will_submit_dna_for=pdf_metadata.get("will_submit_dna_for"),
            type_of_sample=pdf_metadata.get("type_of_sample"),
            human_dna=pdf_metadata.get("human_dna"),
            source_organism=pdf_metadata.get("source_organism"),
            sample_buffer=pdf_metadata.get("sample_buffer"),
            notes=pdf_metadata.get("notes")
        )'''

if old_metadata in content:
    content = content.replace(old_metadata, new_metadata)
    print("✅ Updated SubmissionMetadata creation to include all fields")
else:
    print("⚠️ Could not find exact metadata creation, checking for alternative pattern...")
    # Check if the metadata fields are already there
    if "as_of=pdf_metadata.get" in content:
        print("✅ Service already includes comprehensive fields")
    else:
        print("❌ Could not update metadata creation automatically")
        print("   You may need to manually add the fields to SubmissionMetadata")

# Write back
with open(service_path, 'w') as f:
    f.write(content)

# Now check/update the SubmissionMetadata model
metadata_path = Path("src/domain/models/submission.py")
with open(metadata_path, 'r') as f:
    model_content = f.read()

# Check if all fields exist in the model
required_fields = [
    'as_of', 'expires_on', 'phone', 'billing_address', 'pis', 
    'financial_contacts', 'request_summary', 'forms_text',
    'will_submit_dna_for', 'type_of_sample', 'human_dna',
    'source_organism', 'sample_buffer', 'notes'
]

missing_fields = []
for field in required_fields:
    if f"{field}:" not in model_content:
        missing_fields.append(field)

if missing_fields:
    print(f"\n⚠️ Missing fields in SubmissionMetadata model: {', '.join(missing_fields)}")
    
    # Find the class definition
    import re
    class_pattern = r'class SubmissionMetadata.*?(?=class|\Z)'
    match = re.search(class_pattern, model_content, re.DOTALL)
    
    if match:
        class_text = match.group()
        # Find where to insert (before the last field or before methods)
        insert_point = class_text.rfind("storage_location:")
        if insert_point > 0:
            # Find the end of the storage_location line
            end_of_line = class_text.find('\n', insert_point)
            if end_of_line > 0:
                # Add the missing fields
                new_fields = "\n    # Additional comprehensive fields from PDF extraction"
                for field in missing_fields:
                    new_fields += f"\n    {field}: Optional[str] = None"
                
                new_class = class_text[:end_of_line] + new_fields + class_text[end_of_line:]
                model_content = model_content[:match.start()] + new_class + model_content[match.end():]
                
                with open(metadata_path, 'w') as f:
                    f.write(model_content)
                print(f"✅ Added missing fields to SubmissionMetadata model")
else:
    print("✅ All fields already exist in SubmissionMetadata model")

print("\n✨ Submission service updated to use all PDF fields!")
print("\nNext: Test the upload with a real PDF to see all fields extracted")
