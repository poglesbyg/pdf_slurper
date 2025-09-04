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
            for page_num in range(min(3, len(doc))):
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
        """Parse comprehensive metadata from text content using laboratory PDF patterns."""
        metadata = {}
        lines = [ln.rstrip() for ln in text.split('\n')]
        
        # Comprehensive field mapping for laboratory PDFs
        label_to_field = {
            "identifier": "identifier",
            "as of": "as_of",
            "expires on": "expires_on",
            "service requested": "service_requested",
            "requester": "requester",
            "e-mail": "requester_email",
            "phone": "phone",
            "lab": "lab",
            "billing address": "billing_address",
            "pis": "pis",
            "financial contacts": "financial_contacts",
            "request summary": "request_summary",
            "forms": "forms_text",
            "i will be submitting dna for": "will_submit_dna_for",
            "type of sample": "type_of_sample",
            "do these samples contain human dna?": "human_dna",
            "source organism": "source_organism",
            "sample buffer": "sample_buffer",
        }
        
        # Helper to detect if a line begins a known label
        def detect_label(line: str) -> Optional[str]:
            l = line.strip().lower().rstrip(":")
            for key in label_to_field.keys():
                if l.startswith(key):
                    return key
            return None
        
        # Helper to parse checkbox fields
        def parse_checkboxes(lines_list):
            """Parse checkbox patterns from PDF."""
            checked = []
            for line in lines_list:
                # Look for checked boxes with ☒ or similar patterns
                if "☒" in line or "" in line or "[x]" in line.lower():
                    # Extract the text after the checkbox
                    text = re.sub(r'[☒\[x\]]', '', line, flags=re.IGNORECASE).strip()
                    if text:
                        checked.append(text)
                # Also capture lines that might be selected differently
                elif line.strip() and not "☐" in line and not "[ ]" in line.lower():
                    # Sometimes checked items are just listed without boxes
                    if len(line.strip()) < 100:  # Reasonable length for an option
                        checked.append(line.strip())
            return ", ".join(checked) if checked else None
        
        # Process lines
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            key = detect_label(line)
            if key is None:
                i += 1
                continue
            
            field_name = label_to_field[key]
            
            # Special handling for checkbox fields and human DNA
            if field_name in ["will_submit_dna_for", "type_of_sample", "human_dna", "sample_buffer"]:
                j = i + 1
                checkbox_lines = []
                while j < n and j < i + 20:  # Limit lookahead
                    next_label = detect_label(lines[j])
                    if next_label is not None:
                        break
                    if lines[j].strip():
                        checkbox_lines.append(lines[j])
                    j += 1
                
                # For human_dna, look for Yes or No
                if field_name == "human_dna":
                    for cl in checkbox_lines:
                        cl_lower = cl.lower()
                        if ("yes" in cl_lower and ("☒" in cl or "" in cl)) or ("[x] yes" in cl_lower):
                            metadata[field_name] = "Yes"
                            break
                        elif ("no" in cl_lower and ("☒" in cl or "" in cl)) or ("[x] no" in cl_lower):
                            metadata[field_name] = "No"
                            break
                else:
                    result = parse_checkboxes(checkbox_lines)
                    if result:
                        metadata[field_name] = result
                i = j
                continue
            
            # Check for inline value after colon
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    metadata[field_name] = parts[1].strip()
                    i += 1
                    continue
            
            # Otherwise collect value from next lines
            j = i + 1
            collected = []
            while j < n and j < i + 5:  # Limit lookahead
                next_label = detect_label(lines[j])
                if next_label is not None:
                    break
                if lines[j].strip():
                    collected.append(lines[j].strip())
                j += 1
            
            if collected:
                metadata[field_name] = " ".join(collected)
            i = j
        
        # Also check for organism if contains_human_dna is set
        if metadata.get("human_dna") == "Yes":
            metadata["contains_human_dna"] = True
        elif metadata.get("human_dna") == "No":
            metadata["contains_human_dna"] = False
            
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