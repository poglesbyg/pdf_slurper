#!/usr/bin/env python3
"""
Test script to verify storage location persistence fix
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path

API_URL = "https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu"
TEST_PDF = "HTSF--JL-147_quote_160217072025.pdf"

async def test_storage_location_persistence():
    """Test that storage location persists when retrieving by ID."""
    print("\n" + "="*60)
    print("🔧 TESTING STORAGE LOCATION PERSISTENCE FIX")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        if not Path(TEST_PDF).exists():
            print("❌ Test PDF not found")
            return False
        
        # Create a submission with a unique storage location
        unique_storage = f"Test Storage {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n1️⃣ Creating submission with storage: '{unique_storage}'")
        
        with open(TEST_PDF, 'rb') as f:
            form_data = aiohttp.FormData()
            form_data.add_field('pdf_file', f, filename=TEST_PDF, content_type='application/pdf')
            form_data.add_field('storage_location', unique_storage)
            form_data.add_field('force', 'true')
            form_data.add_field('auto_qc', 'false')
            
            async with session.post(f"{API_URL}/api/v1/submissions/", data=form_data) as response:
                if response.status not in [200, 201]:
                    error = await response.text()
                    print(f"❌ Upload failed: {response.status} - {error[:100]}")
                    return False
                
                data = await response.json()
                submission_id = data.get("id")
                created_storage = data.get("metadata", {}).get("storage_location")
                
                print(f"✅ Created submission: {submission_id}")
                print(f"   Storage on creation: {created_storage}")
        
        # Wait for data to persist
        await asyncio.sleep(2)
        
        # Test 1: Check if it appears in the list
        print(f"\n2️⃣ Checking list endpoint...")
        async with session.get(f"{API_URL}/api/v1/submissions/?limit=100") as response:
            if response.status == 200:
                data = await response.json()
                found_in_list = False
                list_storage = None
                
                for item in data.get("items", []):
                    if item.get("id") == submission_id:
                        found_in_list = True
                        list_storage = item.get("metadata", {}).get("storage_location")
                        break
                
                if found_in_list:
                    print(f"✅ Found in list")
                    print(f"   Storage in list: {list_storage}")
                    if list_storage == unique_storage:
                        print(f"   ✅ Storage matches in list!")
                    else:
                        print(f"   ⚠️ Storage doesn't match in list (expected: {unique_storage})")
                else:
                    print(f"❌ Not found in list")
        
        # Test 2: Get by ID
        print(f"\n3️⃣ Getting submission by ID...")
        async with session.get(f"{API_URL}/api/v1/submissions/{submission_id}") as response:
            if response.status == 200:
                data = await response.json()
                retrieved_storage = data.get("metadata", {}).get("storage_location")
                
                print(f"✅ Retrieved by ID")
                print(f"   Storage on retrieval: {retrieved_storage}")
                
                # Check if storage location persisted
                if retrieved_storage == unique_storage:
                    print(f"\n🎉 SUCCESS: Storage location persisted correctly!")
                    print(f"   Expected: {unique_storage}")
                    print(f"   Got: {retrieved_storage}")
                    return True
                else:
                    print(f"\n❌ FAILED: Storage location not persisted")
                    print(f"   Expected: {unique_storage}")
                    print(f"   Got: {retrieved_storage}")
                    
                    # Additional debugging
                    print(f"\n🔍 Debug info:")
                    print(f"   Full metadata: {json.dumps(data.get('metadata', {}), indent=2)}")
                    return False
            else:
                error = await response.text()
                print(f"❌ Failed to get by ID: {response.status}")
                print(f"   Error: {error[:200]}")
                return False

async def main():
    """Run the storage location persistence test."""
    success = await test_storage_location_persistence()
    
    print("\n" + "="*60)
    if success:
        print("✅ STORAGE LOCATION PERSISTENCE IS FIXED!")
    else:
        print("⚠️ STORAGE LOCATION PERSISTENCE ISSUE REMAINS")
        print("\nPossible causes:")
        print("1. The fix hasn't been deployed yet")
        print("2. There's another issue in the data mapping")
        print("3. The database column isn't being populated")
    print("="*60 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
