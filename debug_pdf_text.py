#!/usr/bin/env python3
"""Debug what text is being extracted from the PDF."""

import fitz  # PyMuPDF
from pathlib import Path

pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")

if pdf_path.exists():
    print(f"📄 Reading: {pdf_path}")
    print("="*60)
    
    # Open with PyMuPDF (fitz)
    with fitz.open(pdf_path) as doc:
        print(f"Pages: {len(doc)}")
        
        # Get text from first few pages
        for page_num in range(min(3, len(doc))):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            print(f"\n📑 Page {page_num + 1} Text (first 1500 chars):")
            print("-"*60)
            print(text[:1500])
            print("-"*60)
            
            # Check for key patterns
            if 'HTSF' in text:
                print("  ✓ Found HTSF")
            if 'Owner:' in text:
                print("  ✓ Found Owner field")
            if 'Joshua Leon' in text:
                print("  ✓ Found Joshua Leon")
            if 'Service Project' in text:
                print("  ✓ Found Service Project")
            if 'submitting DNA for' in text:
                print("  ✓ Found DNA submission section")
            if 'Source Organism' in text:
                print("  ✓ Found Source Organism")
                
else:
    print(f"❌ PDF not found: {pdf_path}")
