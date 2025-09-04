#!/usr/bin/env python3
"""Test the API directly to see the error."""

import requests

# Upload with force
files = {'pdf_file': open('HTSF--JL-147_quote_160217072025.pdf', 'rb')}
data = {
    'storage_location': 'Test Location',
    'force': 'true',
    'auto_qc': 'false'
}

try:
    response = requests.post('http://localhost:8080/api/v1/submissions/', files=files, data=data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 500:
        print("\n❌ Server Error - Check traceback")
    elif response.status_code == 201:
        import json
        result = response.json()
        metadata = result.get('metadata', {})
        
        print("\n✅ Upload successful!")
        print(f"ID: {result.get('id')}")
        print(f"Identifier: {metadata.get('identifier')}")
        print(f"Requester: {metadata.get('requester')}")
        print(f"Email: {metadata.get('requester_email')}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    files['pdf_file'].close()
