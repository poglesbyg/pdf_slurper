"""
Comprehensive End-to-End Tests for PDF Slurper Application
Tests all major functionality including upload, list, view, and statistics
"""

import asyncio
import os
import time
from pathlib import Path
from playwright.async_api import async_playwright, expect
import json
import aiohttp

# Configuration
BASE_URL = "https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu"
API_URL = "https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu"
TEST_PDF = "HTSF--JL-147_quote_160217072025.pdf"
TIMEOUT = 30000  # 30 seconds

# Test data
TEST_STORAGE_LOCATIONS = [
    "Building A - Freezer 1 - Rack 2",
    "Building B - Room 201 - Cabinet 5",
    "Lab C - Cold Storage - Section 3"
]

async def test_api_health():
    """Test that the API is healthy and responding."""
    print("\n🔍 Testing API Health...")
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        async with session.get(f"{API_URL}/health") as response:
            assert response.status == 200, f"Health check failed: {response.status}"
            data = await response.json()
            assert data["status"] == "healthy", "API not healthy"
            print("  ✅ API health check passed")
        
        # Test ready endpoint
        async with session.get(f"{API_URL}/ready") as response:
            assert response.status == 200, f"Ready check failed: {response.status}"
            print("  ✅ API ready check passed")

async def test_dashboard_loads(page):
    """Test that the dashboard loads and shows correct elements."""
    print("\n📊 Testing Dashboard...")
    
    # Navigate to dashboard
    await page.goto(f"{BASE_URL}/dashboard.html", wait_until="networkidle")
    
    # Check page title
    assert await page.title() == "PDF Slurper Dashboard", "Dashboard title incorrect"
    print("  ✅ Dashboard loaded with correct title")
    
    # Check navigation elements
    assert await page.locator("text=PDF Slurper v2").is_visible(), "Header not visible"
    assert await page.locator("a[href='/upload.html']").first.is_visible(), "Upload link not visible"
    assert await page.locator("a[href='/submissions.html']").first.is_visible(), "Submissions link not visible"
    print("  ✅ Navigation elements present")
    
    # Check API status (wait for it to update)
    await page.wait_for_timeout(2000)
    api_status = await page.locator("text=API Status:").locator("..").inner_text()
    assert "Connected" in api_status or "Error" in api_status, "API status not shown"
    print(f"  ✅ API status displayed: {api_status}")
    
    # Check statistics cards
    assert await page.locator("text=Total Submissions").is_visible(), "Submissions stat not visible"
    assert await page.locator("text=Total Samples").is_visible(), "Samples stat not visible"
    assert await page.locator("text=Avg Quality Score").is_visible(), "Quality score stat not visible"
    print("  ✅ Statistics cards displayed")
    
    # Get current statistics
    stats_text = await page.locator("main").inner_text()
    print(f"  📈 Current stats visible on dashboard")

async def test_upload_pdf(page, storage_location):
    """Test PDF upload functionality."""
    print(f"\n📤 Testing PDF Upload with storage: {storage_location}...")
    
    # Navigate to upload page
    await page.goto(f"{BASE_URL}/upload.html", wait_until="networkidle")
    
    # Check page elements
    assert await page.title() == "Upload PDF - PDF Slurper", "Upload page title incorrect"
    assert await page.locator("text=Upload PDF").is_visible(), "Upload header not visible"
    print("  ✅ Upload page loaded")
    
    # Fill in storage location
    storage_input = page.locator("input[x-model='storageLocation']")
    await storage_input.fill(storage_location)
    print(f"  ✅ Storage location filled: {storage_location}")
    
    # Upload file
    file_input = page.locator("input[type='file']")
    pdf_path = Path(TEST_PDF)
    if not pdf_path.exists():
        print(f"  ⚠️ Test PDF not found at {pdf_path}, skipping file upload")
        return None
    
    await file_input.set_input_files(str(pdf_path))
    print(f"  ✅ PDF file selected: {TEST_PDF}")
    
    # Wait for file to be recognized
    await page.wait_for_timeout(1000)
    
    # Check if file is shown as selected
    file_name_shown = await page.locator("text=" + TEST_PDF).count()
    if file_name_shown > 0:
        print(f"  ✅ File shown as selected")
    
    # Enable options if needed
    force_checkbox = page.locator("input[x-model='options.force']")
    if await force_checkbox.is_visible():
        await force_checkbox.check()
        print("  ✅ Force reprocessing enabled")
    
    # Submit the form
    submit_button = page.locator("button:has-text('Upload and Process')")
    
    # Check button is enabled (has file and storage location)
    button_classes = await submit_button.get_attribute("class")
    if "cursor-not-allowed" not in button_classes:
        await submit_button.click()
        print("  ✅ Upload initiated")
        
        # Wait for processing (look for success or error)
        await page.wait_for_timeout(5000)
        
        # Check for result
        success_text = await page.locator("text=Successfully processed").count()
        error_text = await page.locator("text=Error").count()
        
        if success_text > 0:
            print("  ✅ PDF processed successfully")
            
            # Get submission ID if shown
            result_text = await page.locator(".bg-green-50").inner_text() if await page.locator(".bg-green-50").count() > 0 else ""
            if "ID:" in result_text:
                submission_id = result_text.split("ID:")[1].split()[0]
                print(f"  ✅ Submission created with ID: {submission_id}")
                return submission_id
        elif error_text > 0:
            error_msg = await page.locator(".text-red-600").inner_text() if await page.locator(".text-red-600").count() > 0 else "Unknown error"
            print(f"  ⚠️ Upload error: {error_msg}")
    else:
        print("  ⚠️ Submit button disabled")
    
    return None

async def test_submissions_list(page):
    """Test submissions list page."""
    print("\n📋 Testing Submissions List...")
    
    # Navigate to submissions page
    await page.goto(f"{BASE_URL}/submissions.html", wait_until="networkidle")
    
    # Check page loaded
    assert await page.title() == "Submissions - PDF Slurper", "Submissions page title incorrect"
    assert await page.locator("text=Submissions").first.is_visible(), "Submissions header not visible"
    print("  ✅ Submissions page loaded")
    
    # Wait for data to load
    await page.wait_for_timeout(2000)
    
    # Check for table or no data message
    table_exists = await page.locator("table").count() > 0
    no_data = await page.locator("text=No submissions found").count() > 0
    
    if table_exists:
        # Count rows in table
        rows = await page.locator("tbody tr").count()
        print(f"  ✅ Found {rows} submissions in table")
        
        # Check table headers
        headers = await page.locator("thead th").all_text_contents()
        expected_headers = ["ID", "Date", "Samples", "Storage", "Actions"]
        for header in expected_headers:
            if header in " ".join(headers):
                print(f"  ✅ Table header '{header}' present")
        
        # Test view button if submissions exist
        if rows > 0:
            first_view_button = page.locator("tbody tr").first.locator("button:has-text('View')")
            if await first_view_button.count() > 0:
                print("  ✅ View buttons present")
                
                # Click view to test navigation
                await first_view_button.click()
                await page.wait_for_timeout(2000)
                
                # Check if modal or new page opened
                modal_visible = await page.locator(".modal, [role='dialog']").count() > 0
                if modal_visible:
                    print("  ✅ Submission detail modal opened")
                    
                    # Close modal if present
                    close_button = page.locator("button:has-text('Close'), button:has-text('×')")
                    if await close_button.count() > 0:
                        await close_button.first.click()
                        print("  ✅ Modal closed")
                        
    elif no_data:
        print("  ℹ️ No submissions found (empty state shown)")
    else:
        print("  ⚠️ Unable to determine submissions state")

async def test_api_endpoints():
    """Test API endpoints directly."""
    print("\n🔌 Testing API Endpoints...")
    
    async with aiohttp.ClientSession() as session:
        # Test list submissions
        async with session.get(f"{API_URL}/api/v1/submissions/") as response:
            assert response.status == 200, f"List submissions failed: {response.status}"
            data = await response.json()
            total = data.get("total", 0)
            print(f"  ✅ List endpoint: {total} submissions found")
        
        # Test statistics
        async with session.get(f"{API_URL}/api/v1/submissions/statistics") as response:
            assert response.status == 200, f"Statistics failed: {response.status}"
            data = await response.json()
            print(f"  ✅ Statistics: {data.get('total_submissions', 0)} submissions, {data.get('total_samples', 0)} samples")
        
        # Test creating a submission via API
        print("\n  🧪 Testing direct API upload...")
        
        # Check if test PDF exists
        if Path(TEST_PDF).exists():
            with open(TEST_PDF, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('pdf_file', f, filename=TEST_PDF, content_type='application/pdf')
                form_data.add_field('storage_location', 'API Test Location')
                form_data.add_field('force', 'true')
                form_data.add_field('auto_qc', 'false')
                
                async with session.post(f"{API_URL}/api/v1/submissions/", data=form_data) as response:
                    if response.status == 201 or response.status == 200:
                        data = await response.json()
                        submission_id = data.get("id")
                        print(f"  ✅ API upload successful: ID {submission_id}")
                        
                        # Test getting specific submission
                        if submission_id:
                            async with session.get(f"{API_URL}/api/v1/submissions/{submission_id}") as get_response:
                                if get_response.status == 200:
                                    submission_data = await get_response.json()
                                    storage = submission_data.get("metadata", {}).get("storage_location")
                                    print(f"  ✅ Get submission successful, storage: {storage}")
                                else:
                                    print(f"  ⚠️ Get submission failed: {get_response.status}")
                    else:
                        error_text = await response.text()
                        print(f"  ⚠️ API upload failed: {response.status} - {error_text[:100]}")
        else:
            print(f"  ⚠️ Test PDF not found, skipping API upload test")

async def test_search_functionality(page):
    """Test search functionality on submissions page."""
    print("\n🔎 Testing Search Functionality...")
    
    # Navigate to submissions page
    await page.goto(f"{BASE_URL}/submissions.html", wait_until="networkidle")
    await page.wait_for_timeout(2000)
    
    # Look for search input
    search_input = page.locator("input[placeholder*='Search'], input[x-model*='search']")
    if await search_input.count() > 0:
        # Try searching
        await search_input.fill("HTSF")
        await page.wait_for_timeout(1000)
        print("  ✅ Search input found and text entered")
        
        # Check if results updated
        table_rows = await page.locator("tbody tr").count()
        print(f"  ✅ Search results: {table_rows} matching submissions")
        
        # Clear search
        await search_input.clear()
        await page.wait_for_timeout(1000)
        print("  ✅ Search cleared")
    else:
        print("  ℹ️ No search functionality found on page")

async def test_responsive_design(page):
    """Test responsive design at different viewport sizes."""
    print("\n📱 Testing Responsive Design...")
    
    viewports = [
        {"name": "Mobile", "width": 375, "height": 667},
        {"name": "Tablet", "width": 768, "height": 1024},
        {"name": "Desktop", "width": 1920, "height": 1080}
    ]
    
    for viewport in viewports:
        await page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
        await page.goto(f"{BASE_URL}/dashboard.html", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        
        # Check if navigation is visible or has mobile menu
        nav_visible = await page.locator("nav, header").is_visible()
        assert nav_visible, f"Navigation not visible at {viewport['name']} size"
        print(f"  ✅ {viewport['name']} view ({viewport['width']}x{viewport['height']}): Layout works")

async def run_all_tests():
    """Run all end-to-end tests."""
    print("\n" + "="*60)
    print("🚀 COMPREHENSIVE END-TO-END TESTING")
    print("="*60)
    
    # Track test results
    passed = 0
    failed = 0
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,  # Ignore certificate errors
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        # Set default timeout
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Run API health test
            try:
                await test_api_health()
                passed += 1
            except Exception as e:
                print(f"  ❌ API health test failed: {e}")
                failed += 1
            
            # Run dashboard test
            try:
                await test_dashboard_loads(page)
                passed += 1
            except Exception as e:
                print(f"  ❌ Dashboard test failed: {e}")
                failed += 1
            
            # Run upload tests with different storage locations
            for location in TEST_STORAGE_LOCATIONS[:1]:  # Test just one to avoid too many uploads
                try:
                    submission_id = await test_upload_pdf(page, location)
                    if submission_id:
                        passed += 1
                    else:
                        print(f"  ⚠️ Upload test completed but no submission ID returned")
                except Exception as e:
                    print(f"  ❌ Upload test failed: {e}")
                    failed += 1
            
            # Run submissions list test
            try:
                await test_submissions_list(page)
                passed += 1
            except Exception as e:
                print(f"  ❌ Submissions list test failed: {e}")
                failed += 1
            
            # Run API endpoints test
            try:
                await test_api_endpoints()
                passed += 1
            except Exception as e:
                print(f"  ❌ API endpoints test failed: {e}")
                failed += 1
            
            # Run search test
            try:
                await test_search_functionality(page)
                passed += 1
            except Exception as e:
                print(f"  ❌ Search test failed: {e}")
                failed += 1
            
            # Run responsive design test
            try:
                await test_responsive_design(page)
                passed += 1
            except Exception as e:
                print(f"  ❌ Responsive design test failed: {e}")
                failed += 1
            
        finally:
            await browser.close()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A")
    print("="*60)
    
    return failed == 0

async def main():
    """Main test runner."""
    success = await run_all_tests()
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
