#!/usr/bin/env python3
"""Debug PDF text extraction."""

import fitz
from pathlib import Path

pdf_path = Path("HTSF--JL-147_quote_160217072025.pdf")

with fitz.open(pdf_path) as doc:
    print(f"Pages: {len(doc)}")
    
    # Get all text
    full_text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        full_text += page.get_text()
    
    # Search for the missing fields in the text
    search_terms = [
        "Flow Cell",
        "MinION",
        "PromethION",
        "Genome Size",
        "Coverage",
        "basecalled",
        "HAC",
        "SUP",
        "FASTQ",
        "POD5",
        "Data Delivery"
    ]
    
    print("\n🔍 Searching for expected terms in PDF:")
    print("-"*50)
    
    for term in search_terms:
        if term in full_text:
            idx = full_text.find(term)
            # Show context around the term
            start = max(0, idx - 50)
            end = min(len(full_text), idx + 150)
            context = full_text[start:end].replace('\n', ' ')
            print(f"\n✓ Found '{term}':")
            print(f"  Context: ...{context}...")
        else:
            if term.lower() in full_text.lower():
                print(f"\n⚠️ '{term}' found in lowercase")
            else:
                print(f"\n✗ '{term}' NOT FOUND")
    
    # Show the text from page 2 where these fields likely are
    if len(doc) > 1:
        print("\n\n📄 PAGE 2 TEXT (first 2000 chars):")
        print("="*50)
        page2_text = doc.load_page(1).get_text()
        print(page2_text[:2000])
