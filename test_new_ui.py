#!/usr/bin/env python
"""Test script to verify the new Web UI is working with the new API endpoints."""

import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8080"
WEB_BASE = "http://localhost:3000"

def test_api_endpoints():
    """Test that all required API endpoints are working."""
    print("🧪 Testing API Endpoints...")
    
    endpoints_to_test = [
        ("/health", "Health check"),
        ("/ready", "Readiness check"),
        ("/api/v1/submissions/statistics", "Global statistics"),
        ("/api/v1/submissions?limit=10", "List submissions"),
    ]
    
    results = []
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {description}: {endpoint}")
                results.append((endpoint, True, response.status_code))
            else:
                print(f"⚠️ {description}: {endpoint} - Status {response.status_code}")
                results.append((endpoint, False, response.status_code))
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: {endpoint} - {str(e)}")
            results.append((endpoint, False, str(e)))
    
    return results

def test_web_ui():
    """Test that the Web UI is accessible."""
    print("\n🌐 Testing Web UI...")
    
    pages_to_test = [
        ("/", "Dashboard"),
        ("/upload", "Upload page"),
        ("/submissions", "Submissions page"),
    ]
    
    results = []
    
    for endpoint, description in pages_to_test:
        try:
            response = requests.get(f"{WEB_BASE}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {description}: {endpoint}")
                results.append((endpoint, True, response.status_code))
            else:
                print(f"⚠️ {description}: {endpoint} - Status {response.status_code}")
                results.append((endpoint, False, response.status_code))
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: {endpoint} - {str(e)}")
            results.append((endpoint, False, str(e)))
    
    return results

def test_api_web_integration():
    """Test that the Web UI can call the API endpoints."""
    print("\n🔗 Testing API-Web Integration...")
    
    try:
        # Test that statistics endpoint returns expected data
        response = requests.get(f"{API_BASE}/api/v1/submissions/statistics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            expected_fields = ["total_submissions", "total_samples", "status_counts", "qc_status_counts"]
            
            missing_fields = [field for field in expected_fields if field not in data]
            if not missing_fields:
                print("✅ Statistics API returns expected data structure")
                return True
            else:
                print(f"⚠️ Statistics API missing fields: {missing_fields}")
                return False
        else:
            print(f"❌ Statistics API failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Integration test failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing PDF Slurper v2 New UI Integration")
    print("=" * 60)
    
    # Wait for services to be ready
    print("⏳ Waiting for services to start...")
    time.sleep(2)
    
    # Test API
    api_results = test_api_endpoints()
    api_passed = sum(1 for _, success, _ in api_results if success)
    
    # Test Web UI
    web_results = test_web_ui()
    web_passed = sum(1 for _, success, _ in web_results if success)
    
    # Test integration
    integration_passed = test_api_web_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print(f"API Endpoints: {api_passed}/{len(api_results)} passed")
    print(f"Web UI Pages: {web_passed}/{len(web_results)} passed")
    print(f"Integration: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    
    total_tests = len(api_results) + len(web_results) + 1
    total_passed = api_passed + web_passed + (1 if integration_passed else 0)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! The new UI is working correctly.")
        print("\n📱 You can now access:")
        print(f"   Web UI: {WEB_BASE}")
        print(f"   API Docs: {API_BASE}/api/docs")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
