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
        """Parse additional metadata from text content."""
        metadata = {}
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract common metadata patterns
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                
                if "identifier" in key:
                    metadata["identifier"] = value
                elif "requester" in key:
                    metadata["requester"] = value
                elif "lab" in key:
                    metadata["lab"] = value
                elif "service" in key:
                    metadata["service_requested"] = value
        
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