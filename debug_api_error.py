#!/usr/bin/env python3
"""Debug the API error in detail."""

import requests
import traceback

# Upload with force
files = {'pdf_file': open('HTSF--JL-147_quote_160217072025.pdf', 'rb')}
data = {
    'storage_location': 'Debug Test',
    'force': 'true',
    'auto_qc': 'false'
}

print("Sending request...")
response = requests.post('http://localhost:8080/api/v1/submissions/', files=files, data=data)
files['pdf_file'].close()

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 500:
    print("\n❌ Server returned 500 error")
    print("The error is: 'str' object has no attribute 'value'")
    print("\nThis means somewhere in the API, we're trying to call .value on a string.")
    print("The error is caught in the exception handler at line 139.")
    print("\nPossible causes:")
    print("1. One of the metadata fields is a string when we expect an object")
    print("2. The hasattr() check isn't working as expected")
    print("3. There's another place creating SubmissionMetadataResponse we missed")
    
    # Let's test a simpler endpoint
    print("\n\nTesting GET endpoint to see if it works...")
    get_response = requests.get('http://localhost:8080/api/v1/submissions/')
    print(f"GET Status: {get_response.status_code}")
    if get_response.status_code == 200:
        import json
        data = get_response.json()
        print(f"Found {data.get('total', 0)} submissions")
