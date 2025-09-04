#!/usr/bin/env python3
"""Fix the upload endpoint URL in the frontend."""

from pathlib import Path

# Read the current upload.html
upload_path = Path("src/presentation/web/templates/upload.html")
with open(upload_path, 'r') as f:
    content = f.read()

# Fix the upload URL
old_url = "window.API_CONFIG.getApiUrl('/api/v1/submissions/upload')"
new_url = "window.API_CONFIG.getApiUrl('/api/v1/submissions/')"

if old_url in content:
    content = content.replace(old_url, new_url)
    print("✅ Fixed upload URL in upload.html")
else:
    print("⚠️ Upload URL not found or already fixed")

# Write back
with open(upload_path, 'w') as f:
    f.write(content)

# Also add an alias route in the API for clarity
print("\n📝 Adding /upload alias route to API...")

submissions_router = Path("src/presentation/api/v1/routers/submissions.py")
with open(submissions_router, 'r') as f:
    lines = f.readlines()

# Find where to insert the alias route (after the main POST route)
insert_index = None
for i, line in enumerate(lines):
    if 'async def create_submission_from_upload(' in line:
        # Find the end of this function
        brace_count = 0
        for j in range(i, len(lines)):
            if '{' in lines[j]:
                brace_count += lines[j].count('{')
            if '}' in lines[j]:
                brace_count -= lines[j].count('}')
            if lines[j].strip().startswith('return ') or (j > i and lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t')):
                # Found the end, look for the next empty line or next function
                for k in range(j, min(j+20, len(lines))):
                    if lines[k].strip() == '':
                        insert_index = k
                        break
                break
        break

if insert_index:
    # Add the alias route
    alias_route = '''
@router.post(
    "/upload",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF (alias for root POST endpoint)",
    description="Alias endpoint for PDF upload - redirects to main submission creation"
)
async def upload_submission(
    pdf_file: UploadFile = File(..., description="PDF file to process"),
    storage_location: str = Form(..., description="Storage location for samples"),
    force: bool = Form(False, description="Force reprocessing if file already exists"),
    auto_qc: bool = Form(False, description="Automatically apply QC thresholds"),
    min_concentration: float = Form(10.0, description="Minimum concentration threshold"),
    min_volume: float = Form(20.0, description="Minimum volume threshold"), 
    min_ratio: float = Form(1.8, description="Minimum A260/A280 ratio threshold"),
    evaluator: str = Form("", description="QC evaluator name"),
    container: Container = Depends(get_container_dependency)
) -> SubmissionResponse:
    """Alias for create_submission_from_upload - provides clearer URL."""
    return await create_submission_from_upload(
        pdf_file=pdf_file,
        storage_location=storage_location,
        force=force,
        auto_qc=auto_qc,
        min_concentration=min_concentration,
        min_volume=min_volume,
        min_ratio=min_ratio,
        evaluator=evaluator,
        container=container
    )

'''
    lines.insert(insert_index, alias_route)
    
    with open(submissions_router, 'w') as f:
        f.writelines(lines)
    print("✅ Added /upload alias route to API")
else:
    print("⚠️ Could not find insertion point for alias route")
    print("   Manually fixing frontend URL only")

print("\n✨ Upload endpoint fixed!")
print("The upload form will now work correctly.")
