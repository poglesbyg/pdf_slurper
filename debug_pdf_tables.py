#!/usr/bin/env python3
"""Debug PDF table extraction."""

import fitz
from pathlib import Path
import pdfplumber

pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")

print("🔍 Checking table extraction with pdfplumber:")
print("-" * 50)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        if tables:
            print(f"\n📄 Page {page_num}: Found {len(tables)} tables")
            for i, table in enumerate(tables, 1):
                if table and len(table) > 0:
                    print(f"  Table {i}: {len(table)} rows x {len(table[0]) if table[0] else 0} columns")
                    # Show first few rows
                    for row in table[:3]:
                        if row:
                            print(f"    {row[:5]}")  # Show first 5 columns
                            
print("\n🔍 Checking for 'Sample Information' header:")
print("-" * 50)

with fitz.open(pdf_path) as doc:
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        if "Sample Information" in text:
            print(f"✅ Found 'Sample Information' on page {page_num + 1}")
            
            # Show the text around it
            idx = text.find("Sample Information")
            context = text[idx:idx+500].replace('\n', ' ')
            print(f"  Context: {context}")
            
            # Look for table headers
            if "Sample Name" in text or "Volume" in text:
                print(f"  ✅ Found table headers on page {page_num + 1}")
                
print("\n📊 Sample data pattern in text:")
sample_line = "1 1 2 298.9 1.84"  # Example from the PDF
if sample_line in text:
    print("✅ Found sample data pattern!")
else:
    print("⚠️ Sample data pattern not found exactly")
