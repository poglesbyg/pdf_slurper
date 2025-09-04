#!/usr/bin/env python3
"""Test the upload functionality."""

import requests
import sys
from pathlib import Path

# Create a minimal valid PDF
pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Times-Roman>>>>>>>/Contents 4 0 R>>endobj\n4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000115 00000 n\n0000000229 00000 n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n316\n%%EOF"

# Save to temporary file
test_pdf = Path("/tmp/test_upload.pdf")
test_pdf.write_bytes(pdf_content)
print(f"Created test PDF: {test_pdf}")

# Test the upload
url = "http://localhost:8080/api/v1/submissions/"
files = {'pdf_file': ('test.pdf', open(test_pdf, 'rb'), 'application/pdf')}
data = {
    'storage_location': 'Test Location',
    'auto_qc': 'false',
    'force': 'false',
    'min_concentration': '10.0',
    'min_volume': '20.0',
    'min_ratio': '1.8',
    'evaluator': ''
}

print(f"Uploading to: {url}")
try:
    response = requests.post(url, files=files, data=data)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 201 or response.status_code == 200:
        print("✅ Upload successful!")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
