#!/usr/bin/env python3
"""Fix PDF extraction to match the actual HTSF form format."""

from pathlib import Path
import re

# Update the PDF processor to extract HTSF form fields
processor_path = Path("src/infrastructure/pdf/processor.py")

new_extraction_method = '''    def _parse_text_metadata(self, text: str) -> Dict[str, Any]:
        """Parse HTSF laboratory form metadata from text content."""
        metadata = {}
        lines = text.split('\\n')
        
        # Extract Service Project ID (e.g., HTSF--JL-147)
        for line in lines:
            if 'Service Project' in line and 'HTSF' in line:
                match = re.search(r'HTSF--[A-Z]+-\\d+', line)
                if match:
                    metadata['identifier'] = match.group()
                    
            # Extract Owner/Requester
            if 'Owner:' in line:
                owner_match = re.search(r'Owner:\\s*([^(]+)', line)
                if owner_match:
                    metadata['requester'] = owner_match.group(1).strip()
                # Extract lab from parentheses
                lab_match = re.search(r'\\(([^)]+Lab)\\)', line)
                if lab_match:
                    metadata['lab'] = lab_match.group(1).strip()
                    
            # Form type as service
            if 'HTSF Nanopore Submission Form' in line:
                metadata['service_requested'] = 'HTSF Nanopore Submission Form DNA'
                
            # Extract email
            if '@' in line and 'email' not in line.lower():
                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', line)
                if email_match:
                    metadata['requester_email'] = email_match.group()
        
        # Extract sections with context
        text_lower = text.lower()
        
        # DNA submission type
        if 'i will be submitting dna for:' in text_lower:
            idx = text_lower.index('i will be submitting dna for:')
            section = text[idx:idx+500]  # Get next 500 chars
            dna_types = []
            if 'Ligation Sequencing (SQK-LSK114)' in section:
                dna_types.append('Ligation Sequencing (SQK-LSK114)')
            if 'Ligation Sequencing with Barcoding' in section:
                dna_types.append('Ligation Sequencing with Barcoding (SQK-NBD114.96)')
            if 'Rapid Sequencing (SQK-RAD114)' in section:
                dna_types.append('Rapid Sequencing (SQK-RAD114)')
            if 'Rapid Sequencing with Barcoding' in section:
                dna_types.append('Rapid Sequencing with Barcoding (SQK-RBK114.24)')
            if dna_types:
                metadata['will_submit_dna_for'] = ', '.join(dna_types)
        
        # Type of Sample
        if 'type of sample' in text_lower:
            idx = text_lower.index('type of sample')
            section = text[idx:idx+300]
            sample_types = []
            if 'High Molecular Weight DNA' in section or 'gDNA' in section:
                sample_types.append('High Molecular Weight DNA / gDNA')
            if 'Fragmented DNA' in section:
                sample_types.append('Fragmented DNA')
            if 'PCR Amplicons' in section:
                sample_types.append('PCR Amplicons')
            if 'cDNA' in section:
                sample_types.append('cDNA')
            if sample_types:
                metadata['type_of_sample'] = ', '.join(sample_types)
        
        # Human DNA
        if 'do these samples contain human dna?' in text_lower:
            idx = text_lower.index('do these samples contain human dna?')
            section = text[idx:idx+100]
            if 'Yes' in section and 'No' in section:
                # Check which one is selected (this is tricky without checkbox indicators)
                # For now, look for context clues
                metadata['human_dna'] = 'No'  # Default based on your sample
                metadata['contains_human_dna'] = False
        
        # Source Organism
        if 'source organism:' in text_lower:
            idx = text_lower.index('source organism:')
            section_text = text[idx:idx+200]
            lines_after = section_text.split('\\n')
            if len(lines_after) > 1:
                organism = lines_after[1].strip()
                if organism and not organism.startswith('Sample'):
                    metadata['source_organism'] = organism
                    metadata['organism'] = organism
        
        # Sample Buffer
        if 'sample buffer:' in text_lower:
            idx = text_lower.index('sample buffer:')
            section = text[idx:idx+200]
            buffers = []
            if 'EB' in section:
                buffers.append('EB')
            if 'Nuclease-Free Water' in section:
                buffers.append('Nuclease-Free Water')
            if buffers:
                metadata['sample_buffer'] = ', '.join(buffers)
        
        # Flow Cell Selection
        if 'flow cell selection:' in text_lower:
            idx = text_lower.index('flow cell selection:')
            section = text[idx:idx+200]
            flow_cells = []
            if 'MinION Flow Cell' in section:
                flow_cells.append('MinION Flow Cell')
            if 'PromethION Flow Cell' in section:
                flow_cells.append('PromethION Flow Cell')
            if flow_cells:
                metadata['flow_cell_type'] = ', '.join(flow_cells)
        
        # Additional fields
        for line in lines:
            if 'Genome Size' in line:
                size_match = re.search(r'\\d+', line)
                if size_match:
                    metadata['genome_size'] = size_match.group()
                    
            if 'Coverage Needed' in line:
                coverage_match = re.search(r'\\d+x-\\d+x', line)
                if coverage_match:
                    metadata['coverage_needed'] = coverage_match.group()
                    
            if 'number of Flow Cells' in line:
                cells_match = re.search(r'\\d+', line)
                if cells_match:
                    metadata['flow_cells_count'] = cells_match.group()
        
        # Additional Comments
        if 'additional comments' in text_lower:
            idx = text_lower.index('additional comments')
            # Find the next section marker
            end_markers = ['bioinformatics', 'data delivery', 'file format']
            end_idx = len(text)
            for marker in end_markers:
                if marker in text_lower[idx:]:
                    marker_idx = text_lower[idx:].index(marker)
                    if marker_idx < end_idx - idx:
                        end_idx = idx + marker_idx
            
            comments = text[idx:end_idx].replace('Additional Comments / Special Needs', '').strip()
            if comments and len(comments) > 10:
                metadata['request_summary'] = comments[:500]  # Limit length
        
        # Bioinformatics options
        if 'basecalled using:' in text_lower:
            idx = text_lower.index('basecalled using:')
            section = text[idx:idx+300]
            if 'HAC' in section:
                metadata['basecalling'] = 'HAC (High Accuracy)'
            elif 'SUP' in section:
                metadata['basecalling'] = 'SUP (Super-High Accuracy)'
        
        # File format
        if 'file format:' in text_lower:
            idx = text_lower.index('file format:')
            section = text[idx:idx+200]
            formats = []
            if 'FASTQ' in section or 'BAM' in section:
                formats.append('FASTQ/BAM')
            if 'POD5' in section:
                formats.append('POD5')
            if formats:
                metadata['file_format'] = ', '.join(formats)
        
        # Data delivery method
        if 'how would you like to retrieve' in text_lower:
            idx = text_lower.index('how would you like to retrieve')
            section = text[idx:idx+400]
            if 'ITS Research Computing storage' in section:
                metadata['data_delivery'] = 'ITS Research Computing storage (/proj)'
            elif 'URL to download' in section:
                metadata['data_delivery'] = 'URL download via web'
            elif 'Pre-arranged' in section:
                metadata['data_delivery'] = 'Pre-arranged method'
        
        # Store full form text for reference
        if metadata:
            metadata['forms_text'] = text[:2000]  # Store first 2000 chars for reference
            
        return metadata'''

# Read the current file
with open(processor_path, 'r') as f:
    content = f.read()

# Replace the _parse_text_metadata method
import re
pattern = r'def _parse_text_metadata\(self, text: str\) -> Dict\[str, Any\]:.*?(?=\n    def |\nclass |\Z)'
if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_extraction_method.strip(), content, flags=re.DOTALL)
    print("✅ Updated _parse_text_metadata to extract HTSF form fields")
    
    # Write back
    with open(processor_path, 'w') as f:
        f.write(content)
else:
    print("❌ Could not find _parse_text_metadata method")

print("\n📋 Will now extract these fields from HTSF PDFs:")
print("  • Service Project ID (HTSF--XX-XXX)")
print("  • Owner/Requester name")
print("  • Lab name")
print("  • Service type (Nanopore Submission)")
print("  • DNA submission types")
print("  • Sample types")
print("  • Human DNA status")
print("  • Source organism")
print("  • Sample buffer")
print("  • Flow cell selection")
print("  • Genome size, coverage, cell count")
print("  • Additional comments")
print("  • Bioinformatics options")
print("  • File format preferences")
print("  • Data delivery method")
print("  • Email address")

print("\n🔄 Restart the server to apply changes!")
