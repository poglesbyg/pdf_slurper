from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import fitz
import pdfplumber

from .db import Sample, Submission, open_session, find_submission_by_hash
from .hash_utils import sha256_file
from .mapping import derive_sample_mapping


@dataclass
class SlurpResult:
    submission_id: str
    num_samples: int


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = value.strip()
    if text == "":
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def slurp_pdf(pdf_path: Path, db_path: Optional[Path] = None, pages: Optional[str] = None) -> SlurpResult:
    # Gather document metadata and front-matter text
    with fitz.open(pdf_path) as doc:
        metadata = doc.metadata or {}
        page_count = doc.page_count
        # pull first two pages text to parse slurped metadata
        front_text = "\n".join(doc.load_page(i).get_text("text") for i in range(min(2, page_count)))

    def parse_front_matter(block: str) -> dict[str, Optional[str]]:
        lines = [ln.rstrip() for ln in block.splitlines()]
        # Map lowercased label starts to field names
        label_to_field: dict[str, str] = {
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
            "i will be submitting dna for": "will_submit_dna_for_json",
            "type of sample": "type_of_sample_json",
            "do these samples contain human dna?": "human_dna",
            "source organism": "source_organism",
            "sample buffer": "sample_buffer_json",
        }

        # Helper to detect if a line begins a known label
        def detect_label(line: str) -> Optional[str]:
            l = line.strip().lower().rstrip(":")
            for key in label_to_field.keys():
                if l == key:
                    return key
                # inline like "Identifier: value"
                if l.startswith(key + ":"):
                    return key
            return None

        result: dict[str, Optional[str]] = {v: None for v in label_to_field.values()}
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            key = detect_label(line)
            if key is None:
                i += 1
                continue
            field_name = label_to_field[key]
            # Inline value after colon on same line
            m = re.match(rf"^\s*{re.escape(key)}\s*:\s*(.*)$", line, flags=re.IGNORECASE)
            if m and m.group(1).strip():
                result[field_name] = m.group(1).strip()
                i += 1
                continue
            # Otherwise accumulate subsequent non-empty lines until next label
            j = i + 1
            collected: list[str] = []
            while j < n:
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if detect_label(lines[j]) is not None:
                    break
                collected.append(nxt)
                j += 1
            if collected:
                # join with newlines to preserve list choices
                result[field_name] = "\n".join(collected).strip()
            i = j
        return result

    # Parse top-of-doc fields (supports inline and next-line values)
    fm = parse_front_matter(front_text)

    source_hash = sha256_file(pdf_path)

    # Idempotency: if existing submission for same content, update its metadata and return
    with open_session(db_path) as session:
        existing = find_submission_by_hash(session, source_hash)
        if existing:
            # Update metadata fields if newly parsed values are present
            updated = False
            update_fields = {
                "identifier": fm.get("identifier"),
                "as_of": fm.get("as_of"),
                "expires_on": fm.get("expires_on"),
                "service_requested": fm.get("service_requested"),
                "requester": fm.get("requester"),
                "requester_email": fm.get("requester_email"),
                "phone": fm.get("phone"),
                "lab": fm.get("lab"),
                "billing_address": fm.get("billing_address"),
                "pis": fm.get("pis"),
                "financial_contacts": fm.get("financial_contacts"),
                "request_summary": fm.get("request_summary"),
                "forms_text": fm.get("forms_text"),
                "will_submit_dna_for_json": fm.get("will_submit_dna_for_json"),
                "type_of_sample_json": fm.get("type_of_sample_json"),
                "human_dna": fm.get("human_dna"),
                "source_organism": fm.get("source_organism"),
                "sample_buffer_json": fm.get("sample_buffer_json"),
            }
            for key, value in update_fields.items():
                if value and getattr(existing, key) != value:
                    setattr(existing, key, value)
                    updated = True
            if updated:
                session.add(existing)
                session.commit()
            # Count samples
            from sqlmodel import select
            count = len(list(session.exec(select(Sample).where(Sample.submission_id == existing.id))))
            return SlurpResult(submission_id=existing.id, num_samples=count)

    submission = Submission(
        id=_generate_id("sub"),
        source_file=str(pdf_path),
        source_sha256=source_hash,
        title=metadata.get("title"),
        author=metadata.get("author"),
        subject=metadata.get("subject"),
        creator=metadata.get("creator"),
        producer=metadata.get("producer"),
        creation_date=metadata.get("creationDate"),
        page_count=page_count,
        identifier=fm.get("identifier"),
        as_of=fm.get("as_of"),
        expires_on=fm.get("expires_on"),
        service_requested=fm.get("service_requested"),
        requester=fm.get("requester"),
        requester_email=fm.get("requester_email"),
        phone=fm.get("phone"),
        lab=fm.get("lab"),
        billing_address=fm.get("billing_address"),
        pis=fm.get("pis"),
        financial_contacts=fm.get("financial_contacts"),
        request_summary=fm.get("request_summary"),
        forms_text=fm.get("forms_text"),
        will_submit_dna_for_json=fm.get("will_submit_dna_for_json"),
        type_of_sample_json=fm.get("type_of_sample_json"),
        human_dna=fm.get("human_dna"),
        source_organism=fm.get("source_organism"),
        sample_buffer_json=fm.get("sample_buffer_json"),
    )

    # Extract tables with pdfplumber
    total_samples = 0
    with pdfplumber.open(str(pdf_path)) as pdf:
        num_pages = len(pdf.pages)
        page_indices = list(range(num_pages))
        table_index_global = 0
        samples: List[Sample] = []

        for page_index in page_indices:
            page = pdf.pages[page_index]
            tables = page.extract_tables() or []
            for table in tables:
                # Heuristic: detect a sample table by presence of header-like cells
                header = [cell or "" for cell in (table[0] if table else [])]
                normalized_header = ",".join(h.lower().strip() for h in header)
                is_sample_table = (
                    "sample name" in normalized_header and (
                        "qubit" in normalized_header or "nanodrop" in normalized_header
                    )
                )

                if not is_sample_table:
                    table_index_global += 1
                    continue

                mapping = derive_sample_mapping(header)
                col_name = mapping["name"]
                col_volume = mapping["volume_ul"]
                col_qubit = mapping["qubit_ng_per_ul"]
                col_nanodrop = mapping["nanodrop_ng_per_ul"]
                col_260_280 = mapping["a260_a280"]
                col_260_230 = mapping["a260_a230"]

                for row_index, row in enumerate(table[1:]):
                    cells = [(c or "").strip() if isinstance(c, str) else "" for c in row]

                    sample = Sample(
                        id=_generate_id("samp"),
                        submission_id=submission.id,
                        row_index=row_index + (1 if is_sample_table else 0),
                        table_index=table_index_global,
                        page_index=page_index,
                        name=cells[col_name] if col_name is not None and col_name < len(cells) else None,
                        volume_ul=_parse_float(cells[col_volume]) if col_volume is not None and col_volume < len(cells) else None,
                        qubit_ng_per_ul=_parse_float(cells[col_qubit]) if col_qubit is not None and col_qubit < len(cells) else None,
                        nanodrop_ng_per_ul=_parse_float(cells[col_nanodrop]) if col_nanodrop is not None and col_nanodrop < len(cells) else None,
                        a260_a280=_parse_float(cells[col_260_280]) if col_260_280 is not None and col_260_280 < len(cells) else None,
                        a260_a230=_parse_float(cells[col_260_230]) if col_260_230 is not None and col_260_230 < len(cells) else None,
                    )
                    # Skip empty rows that have no meaningful content
                    if any([sample.name, sample.volume_ul, sample.qubit_ng_per_ul, sample.nanodrop_ng_per_ul, sample.a260_a280, sample.a260_a230]):
                        samples.append(sample)

                table_index_global += 1

    # Persist
    with open_session(db_path) as session:
        session.add(submission)
        for s in samples:
            session.add(s)
        session.commit()

    return SlurpResult(submission_id=submission.id, num_samples=len(samples))


