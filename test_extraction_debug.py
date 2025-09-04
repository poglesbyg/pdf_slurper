#!/usr/bin/env python3
"""Debug the full extraction pipeline."""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.pdf.processor import PDFProcessor

async def test():
    processor = PDFProcessor()
    pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")
    
    print("📄 Testing FULL extraction pipeline...")
    print("="*60)
    
    result = await processor.process(pdf_path)
    
    samples = result.get("samples", [])
    
    print(f"Total samples extracted: {len(samples)}")
    print()
    
    if samples:
        print("First 10 samples:")
        print("-"*60)
        for i, sample in enumerate(samples[:10], 1):
            name = sample.get('name', 'Unknown')
            vol = sample.get('volume_ul', 0)
            nano = sample.get('nanodrop_ng_per_ul', 0) 
            qubit = sample.get('qubit_ng_per_ul', 0)
            a260 = sample.get('a260_a280', 0)
            
            print(f"{i:3}. Name: {name:15} Vol: {vol:>4}  Nano: {nano:>6.1f}  Qubit: {qubit:>6.1f}  A260/A280: {a260}")
        
        # Check if all are metadata
        metadata_names = ['Joshua Leon', 'joshleon@unc.edu', 'Mitchell, Charles']
        real_samples = [s for s in samples if not any(meta in str(s.get('name', '')) for meta in metadata_names)]
        
        print()
        print(f"Real samples (not metadata): {len(real_samples)} / {len(samples)}")
        
        if real_samples:
            print()
            print("First 5 real samples:")
            for i, sample in enumerate(real_samples[:5], 1):
                print(f"  {i}. {sample}")

asyncio.run(test())
