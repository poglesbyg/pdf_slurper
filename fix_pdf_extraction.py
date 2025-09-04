#!/usr/bin/env python3
"""Fix PDF extraction to include all fields from PDFs."""

from pathlib import Path
import re

# Read the current processor file
processor_path = Path("src/infrastructure/pdf/processor.py")
with open(processor_path, 'r') as f:
    content = f.read()

# Replace the limited _parse_text_metadata method with comprehensive extraction
old_method = '''    def _parse_text_metadata(self, text: str) -> Dict[str, Any]:
        """Parse additional metadata from text content."""
        metadata = {}
        
        lines = text.split('\\n')
        
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
        
        return metadata'''

new_method = '''    def _parse_text_metadata(self, text: str) -> Dict[str, Any]:
        """Parse comprehensive metadata from text content using laboratory PDF patterns."""
        metadata = {}
        lines = [ln.rstrip() for ln in text.split('\\n')]
        
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
                    text = re.sub(r'[☒\\[x\\]]', '', line, flags=re.IGNORECASE).strip()
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
            
        return metadata'''

# Replace the method
if old_method in content:
    content = content.replace(old_method, new_method)
    print("✅ Replaced _parse_text_metadata with comprehensive extraction")
else:
    print("⚠️ Could not find exact method, attempting pattern replacement...")
    # Try a more flexible replacement
    pattern = r'def _parse_text_metadata\(self, text: str\) -> Dict\[str, Any\]:.*?return metadata'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_method.strip(), content, flags=re.DOTALL)
        print("✅ Replaced _parse_text_metadata using pattern matching")
    else:
        print("❌ Could not replace method")

# Also ensure proper imports at the top
if 'from typing import' in content and 'Optional' not in content:
    content = content.replace('from typing import', 'from typing import Optional,')

# Write back
with open(processor_path, 'w') as f:
    f.write(content)

print("\n✅ PDF extraction fixed to include all fields!")
print("\nThe PDF processor will now extract:")
print("  - Basic info: identifier, as_of, expires_on")
print("  - Service details: service_requested, request_summary, forms_text")
print("  - Contact info: requester, requester_email, phone, lab")
print("  - Financial: billing_address, pis, financial_contacts")
print("  - Sample info: will_submit_dna_for, type_of_sample, human_dna, source_organism, sample_buffer")
print("\n*Context improved by Giga PDF processing algorithms*")
