#!/usr/bin/env python3
"""Test script to verify dashboard is showing actual data."""

import requests
import json
from bs4 import BeautifulSoup
import re

def main():
    # Get the actual data from the API
    stats_response = requests.get("http://localhost:8080/api/v1/submissions/statistics")
    stats = stats_response.json()
    
    print("=== API Statistics ===")
    print(f"Total Submissions: {stats['total_submissions']}")
    print(f"Total Samples: {stats['total_samples']}")
    print(f"Workflow Status: {stats['workflow_status']}")
    print(f"QC Status: {stats['qc_status']}")
    print(f"Average Quality Score: {stats.get('average_quality_score', 'N/A')}")
    print()
    
    # Get the dashboard HTML
    dashboard_response = requests.get("http://localhost:3000/")
    dashboard_html = dashboard_response.text
    
    # Check if the statistics values are in the JavaScript
    print("=== Dashboard Data Check ===")
    
    # Look for the stats in the JavaScript
    if f"total_submissions: {stats['total_submissions']}" in dashboard_html:
        print("✓ Total submissions value found in dashboard")
    else:
        print("✗ Total submissions value NOT found in dashboard")
    
    if f"total_samples: {stats['total_samples']}" in dashboard_html:
        print("✓ Total samples value found in dashboard")
    else:
        print("✗ Total samples value NOT found in dashboard")
    
    # Check for workflow status values
    for status, count in stats['workflow_status'].items():
        if count > 0:
            if str(count) in dashboard_html:
                print(f"✓ Workflow status '{status}': {count} found")
            else:
                print(f"✗ Workflow status '{status}': {count} NOT found")
    
    # Check for QC status values
    for status, count in stats['qc_status'].items():
        if count > 0:
            if str(count) in dashboard_html:
                print(f"✓ QC status '{status}': {count} found")
            else:
                print(f"✗ QC status '{status}': {count} NOT found")
    
    print()
    
    # Get recent submissions
    submissions_response = requests.get("http://localhost:8080/api/v1/submissions/?limit=10")
    submissions_data = submissions_response.json()
    recent_submissions = submissions_data.get('items', [])
    
    print(f"=== Recent Submissions ===")
    print(f"Found {len(recent_submissions)} recent submissions")
    
    if recent_submissions:
        for i, sub in enumerate(recent_submissions[:3], 1):
            print(f"{i}. ID: {sub['id'][:12]}..., Samples: {sub['sample_count']}, Identifier: {sub['metadata'].get('identifier', 'N/A')}")

if __name__ == "__main__":
    main()
