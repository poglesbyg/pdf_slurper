"""PDF processing infrastructure module."""

import hashlib
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import only what we need for now
# from ...domain.models.submission import Submission, SubmissionMetadata, PDFSource
# from ...domain.models.sample import Sample, Measurements
# from ...domain.models.value_objects import (
#     SubmissionId, SampleId, Concentration, Volume, QualityRatio
# )
from ...shared.exceptions import PDFExtractionException


class PDFProcessor:
    """Process PDF files and extract data."""
    
    def __init__(self):
        """Initialize PDF processor."""
        pass
    
    async def process(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a PDF file and return extracted data.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted data including file_hash
        """
        try:
            # Calculate file hash first
            file_hash = self._calculate_hash(pdf_path)
            
            # Extract basic metadata
            metadata = self._extract_metadata(pdf_path)
            
            # Extract tables
            tables = self._extract_tables(pdf_path)
            
            # Process tables into samples
            samples = self._process_tables_to_samples(tables, pdf_path)
            
            return {
                "file_hash": file_hash,
                "metadata": metadata,
                "samples": samples,
                "pdf_source": {
                    "file_path": str(pdf_path),
                    "file_hash": file_hash,
                    "file_size": pdf_path.stat().st_size,
                    "modification_time": datetime.fromtimestamp(pdf_path.stat().st_mtime),
                    "page_count": self._get_page_count(pdf_path)
                }
            }
            
        except Exception as e:
            raise PDFExtractionException(f"Failed to process PDF: {str(e)}", str(pdf_path))
    
    def _extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        try:
            doc = fitz.open(pdf_path)
            
            metadata = {
                "title": doc.metadata.get("title"),
                "author": doc.metadata.get("author"),
                "subject": doc.metadata.get("subject"),
                "creator": doc.metadata.get("creator"),
                "producer": doc.metadata.get("producer"),
                "creation_date": doc.metadata.get("creationDate"),
                "modification_date": doc.metadata.get("modDate")
            }
            
            # Extract text from first few pages for additional metadata
            text_content = ""
            # Extract text from ALL pages to capture all fields
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_content += page.get_text()
            
            # Parse additional metadata from text
            additional_metadata = self._parse_text_metadata(text_content)
            metadata.update(additional_metadata)
            
            doc.close()
            return metadata
            
        except Exception as e:
            return {"error": f"Failed to extract metadata: {str(e)}"}
    
    def _extract_tables(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract tables from PDF."""
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_num, table in enumerate(page_tables):
                        if table and len(table) > 1:  # Skip empty or single-row tables
                            tables.append({
                                "page": page_num + 1,
                                "table": table_num + 1,
                                "data": table,
                                "headers": table[0] if table else [],
                                "rows": table[1:] if len(table) > 1 else []
                            })
        except Exception as e:
            # Return empty tables if extraction fails
            return []
        
        return tables
    
    def _process_tables_to_samples(self, tables: List[Dict[str, Any]], pdf_path: Path) -> List[Dict[str, Any]]:
        """Process extracted tables into sample data."""
        samples = []
        
        for table in tables:
            if not table["rows"]:
                continue
                
            # Look for sample data in table rows
            for row_idx, row in enumerate(table["rows"]):
                sample_data = self._extract_sample_from_row(row, table["headers"])
                if sample_data:
                    sample_data.update({
                        "row_index": row_idx + 1,
                        "table_index": table["table"],
                        "page_index": table["page"]
                    })
                    samples.append(sample_data)
        
        return samples
    
    def _extract_sample_from_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Extract sample data from a table row."""
        if not row or not headers:
            return None
        
        # Look for sample identifiers or measurements
        sample_data = {}
        
        for i, (header, value) in enumerate(zip(headers, row)):
            if not header or not value:
                continue
                
            header_lower = header.lower().strip()
            value_str = str(value).strip()
            
            # Extract sample name/ID
            if any(keyword in header_lower for keyword in ["sample", "id", "name", "well"]):
                sample_data["name"] = value_str
            
            # Extract volume
            elif any(keyword in header_lower for keyword in ["volume", "ul", "μl"]):
                try:
                    volume = float(value_str.replace("μL", "").replace("ul", "").strip())
                    sample_data["volume_ul"] = volume
                except ValueError:
                    pass
            
            # Extract concentration
            elif any(keyword in header_lower for keyword in ["qubit", "concentration", "ng/ul"]):
                try:
                    conc = float(value_str.replace("ng/μL", "").replace("ng/ul", "").strip())
                    sample_data["qubit_ng_per_ul"] = conc
                except ValueError:
                    pass
            
            # Extract quality ratios
            elif "a260/a280" in header_lower or "260/280" in header_lower:
                try:
                    ratio = float(value_str)
                    sample_data["a260_a280"] = ratio
                except ValueError:
                    pass
        
        # Only return if we found meaningful data
        if sample_data and (sample_data.get("name") or sample_data.get("volume_ul") or sample_data.get("qubit_ng_per_ul")):
            return sample_data
        
        return None
    
    def _parse_text_metadata(self, text: str) -> Dict[str, Any]:
        """Parse HTSF laboratory form metadata from text content."""
        metadata = {}
        lines = text.split('\n')
        
        # Extract HTSF identifier
        for line in lines:
            if 'Identifier:' in line and 'HTSF' in line:
                import re
                match = re.search(r'HTSF--[A-Z]+-\d+', line)
                if match:
                    metadata['identifier'] = match.group()
                    
            # Extract Requester (from "Requester:" line)
            if 'Requester:' in line:
                # Look at the next line for the value
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    metadata['requester'] = lines[idx + 1].strip()
                    
            # Extract Lab (from "Lab:" line)  
            if line.startswith('Lab:'):
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    metadata['lab'] = lines[idx + 1].strip()
                    
            # Extract Service Requested
            if 'Service Requested:' in line:
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    metadata['service_requested'] = lines[idx + 1].strip()
                
            # Extract email (from "E-mail:" line)
            if 'E-mail:' in line:
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    email = lines[idx + 1].strip()
                    if '@' in email:
                        metadata['requester_email'] = email
        
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
            lines_after = section_text.split('\n')
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
                import re
                size_match = re.search(r'\d+', line)
                if size_match:
                    metadata['genome_size'] = size_match.group()
                    
            if 'Coverage Needed' in line:
                import re
                coverage_match = re.search(r'\d+x-\d+x', line)
                if coverage_match:
                    metadata['coverage_needed'] = coverage_match.group()
                    
            if 'number of Flow Cells' in line:
                import re
                cells_match = re.search(r'\d+', line)
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
            
        return metadata
    
    def _calculate_hash(self, pdf_path: Path) -> str:
        """Calculate SHA256 hash of PDF file."""
        hash_sha256 = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _get_page_count(self, pdf_path: Path) -> int:
        """Get page count of PDF."""
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0