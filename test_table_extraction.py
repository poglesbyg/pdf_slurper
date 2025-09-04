#!/usr/bin/env python3
"""Test table extraction directly."""

import pdfplumber
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")

print("📄 Testing table extraction from HTSF PDF")
print("="*60)

with pdfplumber.open(pdf_path) as pdf:
    # Focus on page 2 where the sample table is
    page = pdf.pages[1]  # Page 2 (0-indexed)
    tables = page.extract_tables()
    
    if tables:
        table = tables[0]  # First table on page 2
        
        print(f"Table has {len(table)} rows")
        print()
        
        # Show headers
        headers = table[0] if table else []
        print("Headers:", headers)
        print("-"*60)
        
        # Show first 5 data rows
        print("First 5 data rows:")
        for i, row in enumerate(table[1:6], 1):
            print(f"Row {i}: {row}")
        
        # Now test the extraction logic
        print("\n" + "="*60)
        print("Testing extraction logic:")
        print("-"*60)
        
        from src.infrastructure.pdf.processor import PDFProcessor
        
        processor = PDFProcessor()
        
        # Test extracting a sample from a row
        test_row = table[1]  # First data row
        sample = processor._extract_sample_from_row(test_row, headers)
        
        print(f"Test row: {test_row}")
        print(f"Extracted sample: {sample}")
        
        # Test more rows
        print("\nExtracting first 5 samples:")
        for i, row in enumerate(table[1:6], 1):
            sample = processor._extract_sample_from_row(row, headers)
            if sample:
                print(f"  {i}. {sample}")
            else:
                print(f"  {i}. No data extracted from: {row}")
