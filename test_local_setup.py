#!/usr/bin/env python3
"""Test script to verify local setup is working correctly."""

import time
import requests
import json
from pathlib import Path

def test_api_health():
    """Test if API is running."""
    try:
        response = requests.get("http://localhost:8080/health")
        if response.status_code == 200:
            print("✅ API health check passed")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ API is not running. Please start it with: python3 start_combined.py")
        return False
    return False

def test_api_endpoints():
    """Test main API endpoints."""
    base_url = "http://localhost:8080/api/v1"
    
    # Test submissions endpoint
    try:
        response = requests.get(f"{base_url}/submissions/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Submissions endpoint working ({data.get('total', 0)} submissions found)")
        else:
            print(f"⚠️  Submissions endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing submissions: {e}")
    
    # Test statistics endpoint
    try:
        response = requests.get(f"{base_url}/submissions/statistics")
        if response.status_code == 200:
            print("✅ Statistics endpoint working")
        else:
            print(f"⚠️  Statistics endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing statistics: {e}")

def test_pdf_upload():
    """Test PDF upload functionality."""
    # Find a test PDF
    test_pdfs = list(Path(".").glob("*.pdf"))
    if not test_pdfs:
        print("⚠️  No PDF files found for testing")
        return
    
    test_pdf = test_pdfs[0]
    print(f"📄 Testing upload with: {test_pdf.name}")
    
    try:
        with open(test_pdf, 'rb') as f:
            files = {'pdf_file': (test_pdf.name, f, 'application/pdf')}
            data = {
                'storage_location': 'Test Location - Local',
                'force': 'false'
            }
            response = requests.post(
                "http://localhost:8080/api/v1/submissions/",
                files=files,
                data=data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"✅ PDF upload successful!")
                print(f"   - Submission ID: {result.get('id')}")
                print(f"   - Sample count: {result.get('sample_count')}")
                return result.get('id')
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error uploading PDF: {e}")
    
    return None

def test_submission_retrieval(submission_id):
    """Test retrieving a specific submission."""
    if not submission_id:
        print("⚠️  No submission ID to test retrieval")
        return
    
    try:
        response = requests.get(f"http://localhost:8080/api/v1/submissions/{submission_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Submission retrieval working")
            print(f"   - ID: {data.get('id')}")
            print(f"   - Identifier: {data.get('metadata', {}).get('identifier')}")
            print(f"   - Requester: {data.get('metadata', {}).get('requester')}")
        else:
            print(f"❌ Failed to retrieve submission: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving submission: {e}")

def test_samples_retrieval(submission_id):
    """Test retrieving samples for a submission."""
    if not submission_id:
        print("⚠️  No submission ID to test sample retrieval")
        return
    
    try:
        response = requests.get(f"http://localhost:8080/api/v1/submissions/{submission_id}/samples")
        if response.status_code == 200:
            data = response.json()
            samples = data.get('items', [])
            print(f"✅ Samples retrieval working ({len(samples)} samples found)")
            if samples:
                print(f"   - First sample: {samples[0].get('name')}")
        else:
            print(f"❌ Failed to retrieve samples: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving samples: {e}")

def test_web_ui():
    """Test if web UI pages are accessible."""
    pages = [
        ("Dashboard", "http://localhost:8080/"),
        ("Upload", "http://localhost:8080/upload"),
        ("Submissions", "http://localhost:8080/submissions"),
    ]
    
    for name, url in pages:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ {name} page accessible")
            else:
                print(f"⚠️  {name} page returned: {response.status_code}")
        except Exception as e:
            print(f"❌ Error accessing {name}: {e}")

def main():
    """Run all tests."""
    print("\n🧪 Testing PDF Slurper Local Setup")
    print("=" * 40)
    
    # Test 1: Check API health
    print("\n1. API Health Check:")
    if not test_api_health():
        print("\n⚠️  Please start the server first:")
        print("   python3 start_combined.py")
        return
    
    # Wait a moment for API to be fully ready
    time.sleep(1)
    
    # Test 2: API endpoints
    print("\n2. API Endpoints:")
    test_api_endpoints()
    
    # Test 3: Web UI
    print("\n3. Web UI Pages:")
    test_web_ui()
    
    # Test 4: PDF Upload
    print("\n4. PDF Upload Test:")
    submission_id = test_pdf_upload()
    
    # Test 5: Submission retrieval
    if submission_id:
        print("\n5. Submission Retrieval:")
        test_submission_retrieval(submission_id)
        
        print("\n6. Samples Retrieval:")
        test_samples_retrieval(submission_id)
    
    print("\n" + "=" * 40)
    print("🎉 Testing complete!")
    print("\nYou can now:")
    print(f"  1. View dashboard at: http://localhost:8080/")
    print(f"  2. Upload PDFs at: http://localhost:8080/upload")
    if submission_id:
        print(f"  3. View your test submission at: http://localhost:8080/submission/{submission_id}")
    print(f"  4. Check API docs at: http://localhost:8080/api/docs")
    print()

if __name__ == "__main__":
    main()
