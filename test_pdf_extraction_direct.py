#!/usr/bin/env python3
"""Test PDF extraction directly."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.pdf.processor import PDFProcessor
import asyncio

async def test():
    processor = PDFProcessor()
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"📄 Processing: {pdf_path}")
    
    # Process the PDF
    result = await processor.process(pdf_path)
    
    print("\n📋 Extracted Metadata:")
    print("="*60)
    
    metadata = result.get("metadata", {})
    
    # Show all metadata fields
    if metadata:
        for key, value in metadata.items():
            if value:
                value_str = str(value)[:100] if len(str(value)) > 100 else str(value)
                print(f"  {key}: {value_str}")
    else:
        print("  No metadata extracted")
    
    print("\n📦 Samples:")
    samples = result.get("samples", [])
    print(f"  Found {len(samples)} samples")
    
    print("\n📄 PDF Source:")
    pdf_source = result.get("pdf_source", {})
    print(f"  File hash: {result.get('file_hash', 'N/A')}")
    print(f"  Page count: {pdf_source.get('page_count', 'N/A')}")

# Run the test
asyncio.run(test())
