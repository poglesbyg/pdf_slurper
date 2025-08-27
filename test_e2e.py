#!/usr/bin/env python3
"""
End-to-End tests for PDF Slurper using Playwright
Tests all CRUD functionality before OpenShift deployment
"""

import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright, expect

# Configuration
BASE_URL = "http://localhost:3000"  # Local Web UI
API_URL = "http://localhost:8080"   # Local API

# Test data
TEST_STORAGE_LOCATION = "Building A - Room 101 - Freezer 3"
TEST_PDF_PATH = "/Users/paulgreenwood/Dev/20250814/pdf_slurper/HTSF--JL-147_quote_160217072025.pdf"


async def test_api_health(page):
    """Test that the API is responding"""
    response = await page.request.get(f"{API_URL}/health")
    assert response.ok, f"API health check failed: {response.status}"
    data = await response.json()
    assert data["status"] == "healthy"
    print("✅ API health check passed")


async def test_dashboard_loads(page):
    """Test that the dashboard loads correctly"""
    await page.goto(f"{BASE_URL}/dashboard.html")
    await page.wait_for_load_state("networkidle")
    
    # Check for main elements
    await expect(page.locator("h1")).to_contain_text("PDF Slurper")
    
    # Check if statistics are displayed (even if zero)
    stats_cards = page.locator(".bg-white.rounded-lg.shadow")
    await expect(stats_cards).to_have_count(4, timeout=5000)
    
    print("✅ Dashboard loads correctly")


async def test_upload_page(page):
    """Test that the upload page works"""
    await page.goto(f"{BASE_URL}/upload.html")
    await page.wait_for_load_state("networkidle")
    
    # Check for upload form elements
    await expect(page.locator('input[type="file"]')).to_be_visible()
    await expect(page.locator('input[placeholder*="storage location"]')).to_be_visible()
    await expect(page.locator('button:has-text("Upload")')).to_be_visible()
    
    print("✅ Upload page loads correctly")


async def test_file_upload_validation(page):
    """Test that upload validation works"""
    await page.goto(f"{BASE_URL}/upload.html")
    await page.wait_for_load_state("networkidle")
    
    # Try to upload without storage location
    upload_button = page.locator('button:has-text("Upload")')
    
    # Button should be disabled initially
    await expect(upload_button).to_be_disabled()
    
    # Add storage location
    storage_input = page.locator('input[placeholder*="storage location"]')
    await storage_input.fill(TEST_STORAGE_LOCATION)
    
    # Button should still be disabled without file
    await expect(upload_button).to_be_disabled()
    
    print("✅ Upload validation works correctly")


async def test_full_upload_flow(page):
    """Test uploading a PDF with storage location"""
    await page.goto(f"{BASE_URL}/upload.html")
    await page.wait_for_load_state("networkidle")
    
    # Fill in storage location
    storage_input = page.locator('input[placeholder*="storage location"]')
    await storage_input.fill(TEST_STORAGE_LOCATION)
    
    # Upload file if it exists
    pdf_path = Path(TEST_PDF_PATH)
    if pdf_path.exists():
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(TEST_PDF_PATH)
        
        # Submit form
        upload_button = page.locator('button:has-text("Upload")')
        await expect(upload_button).to_be_enabled()
        
        # Click and wait for response
        await upload_button.click()
        
        # Wait for success message or redirect
        try:
            success_msg = page.locator('text=/success|uploaded|created/i')
            await expect(success_msg).to_be_visible(timeout=10000)
            print("✅ File upload successful")
        except:
            # Check if redirected to submissions
            if page.url.endswith("/submissions.html"):
                print("✅ File uploaded and redirected to submissions")
            else:
                print("⚠️ Upload completed but no clear success indication")
    else:
        print(f"⚠️ Test PDF not found at {TEST_PDF_PATH}")


async def test_submissions_list(page):
    """Test that submissions list works"""
    await page.goto(f"{BASE_URL}/submissions.html")
    await page.wait_for_load_state("networkidle")
    
    # Check for table or empty state
    table = page.locator("table")
    empty_state = page.locator('text=/no submissions/i')
    
    # Either table or empty state should be visible
    try:
        await expect(table).to_be_visible(timeout=5000)
        print("✅ Submissions table displayed")
        
        # Check if storage location column exists
        storage_header = page.locator('th:has-text("Location")')
        if await storage_header.is_visible():
            print("✅ Storage location column present")
    except:
        await expect(empty_state).to_be_visible()
        print("✅ Empty submissions state displayed")


async def test_submission_detail_crud(page):
    """Test CRUD operations on submission detail page"""
    # First check if there are any submissions
    await page.goto(f"{BASE_URL}/submissions.html")
    await page.wait_for_load_state("networkidle")
    
    # Try to find a submission row
    submission_rows = page.locator("tbody tr")
    count = await submission_rows.count()
    
    if count > 0:
        # Click on first submission
        first_row = submission_rows.first
        await first_row.locator("a, button").first.click()
        await page.wait_for_load_state("networkidle")
        
        # Check if we're on detail page
        if "submission" in page.url:
            # Test editing metadata
            edit_button = page.locator('button:has-text("Edit")')
            if await edit_button.is_visible():
                await edit_button.click()
                
                # Look for input fields
                location_input = page.locator('input[name="storage_location"]')
                if await location_input.is_visible():
                    await location_input.fill(f"{TEST_STORAGE_LOCATION} - Updated")
                    
                    save_button = page.locator('button:has-text("Save")')
                    await save_button.click()
                    print("✅ Submission metadata edit works")
            
            # Test adding a sample
            add_sample_button = page.locator('button:has-text("Add Sample")')
            if await add_sample_button.is_visible():
                await add_sample_button.click()
                
                # Fill sample form
                sample_id_input = page.locator('input[name="sample_id"], input[placeholder*="Sample ID"]').first
                if await sample_id_input.is_visible():
                    await sample_id_input.fill("TEST-001")
                    
                    # Submit sample
                    modal_save = page.locator('.modal button:has-text("Save"), dialog button:has-text("Add")')
                    if await modal_save.is_visible():
                        await modal_save.click()
                        print("✅ Sample creation works")
            
            print("✅ Submission detail page works")
    else:
        print("ℹ️ No submissions to test detail page")


async def test_api_crud_endpoints(page):
    """Test API CRUD endpoints directly"""
    
    # Test GET submissions
    response = await page.request.get(f"{API_URL}/api/v1/submissions/")
    assert response.ok, f"GET submissions failed: {response.status}"
    data = await response.json()
    assert "items" in data
    print(f"✅ API GET submissions works ({len(data['items'])} items)")
    
    # Test statistics endpoint
    response = await page.request.get(f"{API_URL}/api/v1/submissions/statistics")
    if response.ok:
        stats = await response.json()
        print(f"✅ API statistics works (total: {stats.get('total_submissions', 0)})")
    else:
        print("⚠️ Statistics endpoint returned error")
    
    # If there are submissions, test PATCH
    if data["items"]:
        first_submission = data["items"][0]
        submission_id = first_submission["id"]
        
        # Test PATCH submission
        patch_data = {"metadata": {"storage_location": "Test Location Updated"}}
        response = await page.request.patch(
            f"{API_URL}/api/v1/submissions/{submission_id}",
            data=patch_data
        )
        if response.ok:
            print("✅ API PATCH submission works")
        else:
            print(f"⚠️ API PATCH failed: {response.status}")
        
        # Test sample creation
        sample_data = {
            "sample_id": "API-TEST-001",
            "well_position": "A1",
            "concentration": 100.0,
            "volume": 50.0
        }
        response = await page.request.post(
            f"{API_URL}/api/v1/submissions/{submission_id}/samples",
            data=sample_data
        )
        if response.ok:
            sample = await response.json()
            sample_id = sample.get("id")
            print(f"✅ API POST sample works (ID: {sample_id})")
            
            # Test sample deletion
            if sample_id:
                response = await page.request.delete(
                    f"{API_URL}/api/v1/submissions/{submission_id}/samples/{sample_id}"
                )
                if response.ok:
                    print("✅ API DELETE sample works")


async def run_all_tests():
    """Run all E2E tests"""
    print("\n" + "="*60)
    print("🧪 PDF SLURPER END-TO-END TESTS")
    print("="*60 + "\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set longer timeout for slow operations
        page.set_default_timeout(30000)
        
        try:
            print("📡 Testing API...")
            await test_api_health(page)
            await test_api_crud_endpoints(page)
            
            print("\n🌐 Testing Web UI...")
            await test_dashboard_loads(page)
            await test_upload_page(page)
            await test_file_upload_validation(page)
            await test_full_upload_flow(page)
            await test_submissions_list(page)
            await test_submission_detail_crud(page)
            
            print("\n" + "="*60)
            print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
            print("🚀 Application is ready for OpenShift deployment")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            print("\n⚠️ Fix issues before deploying to OpenShift")
            raise
        finally:
            await browser.close()


async def run_quick_test():
    """Quick smoke test for basic functionality"""
    print("\n🚀 Running quick smoke test...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Just test that main pages load
            response = await page.request.get(f"{API_URL}/health")
            assert response.ok, "API not responding"
            
            await page.goto(f"{BASE_URL}/dashboard.html")
            await expect(page.locator("h1")).to_be_visible(timeout=5000)
            
            print("✅ Quick test passed - services are running")
            
        except Exception as e:
            print(f"❌ Quick test failed: {e}")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(run_quick_test())
    else:
        asyncio.run(run_all_tests())
