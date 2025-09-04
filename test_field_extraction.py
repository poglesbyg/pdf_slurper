#!/usr/bin/env python3
"""Test if the new fields are being extracted from PDF."""

from pathlib import Path
import sys
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.pdf.processor import PDFProcessor

async def test():
    processor = PDFProcessor()
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    
    print("📄 Extracting from PDF...")
    result = await processor.process(pdf_path)
    
    metadata = result.get("metadata", {})
    
    print("\n🔬 Checking NEW field extraction:")
    print("-"*50)
    
    new_fields = [
        'flow_cell_type',
        'genome_size',
        'coverage_needed',
        'flow_cells_count',
        'basecalling',
        'file_format',
        'data_delivery'
    ]
    
    for field in new_fields:
        value = metadata.get(field)
        if value:
            print(f"✓ {field}: {value}")
        else:
            print(f"✗ {field}: Not extracted")
    
    print("\n📄 Sample of PDF text:")
    text = result.get("text", "")[:3000]
    
    # Check if the text contains the expected patterns
    if "Flow Cell Selection" in text:
        print("  ✓ Found 'Flow Cell Selection' in text")
    if "MinION" in text:
        print("  ✓ Found 'MinION' in text")
    if "Genome Size" in text:
        print("  ✓ Found 'Genome Size' in text")
    if "Coverage Needed" in text:
        print("  ✓ Found 'Coverage Needed' in text")
    if "basecalled using" in text:
        print("  ✓ Found 'basecalled using' in text")
    if "HAC" in text:
        print("  ✓ Found 'HAC' in text")
    if "File Format" in text:
        print("  ✓ Found 'File Format' in text")
    
    # Show a sample of the text
    print("\nText sample around Flow Cell:")
    idx = text.lower().find("flow cell")
    if idx >= 0:
        print(text[idx:idx+300])

asyncio.run(test())
