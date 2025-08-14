from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .db import Sample, Submission


def submission_to_json(submission: Submission, samples: Iterable[Sample]) -> str:
	data = {
		"submission": {
			"id": submission.id,
			"created_at": submission.created_at.isoformat(),
			"source_file": submission.source_file,
			"source_sha256": getattr(submission, "source_sha256", None),
			"title": submission.title,
			"author": submission.author,
			"subject": submission.subject,
			"creator": submission.creator,
			"producer": submission.producer,
			"creation_date": submission.creation_date,
			"page_count": submission.page_count,
			"identifier": submission.identifier,
			"as_of": submission.as_of,
			"expires_on": submission.expires_on,
			"service_requested": submission.service_requested,
			"requester": submission.requester,
			"requester_email": submission.requester_email,
			"phone": submission.phone,
			"lab": submission.lab,
			"billing_address": submission.billing_address,
			"pis": submission.pis,
			"financial_contacts": submission.financial_contacts,
			"request_summary": submission.request_summary,
			"forms_text": submission.forms_text,
			"will_submit_dna_for_json": submission.will_submit_dna_for_json,
			"type_of_sample_json": submission.type_of_sample_json,
			"human_dna": submission.human_dna,
			"source_organism": submission.source_organism,
			"sample_buffer_json": submission.sample_buffer_json,
		},
		"samples": [
			{
				"id": s.id,
				"submission_id": s.submission_id,
				"row_index": s.row_index,
				"table_index": s.table_index,
				"page_index": s.page_index,
				"name": s.name,
				"volume_ul": s.volume_ul,
				"qubit_ng_per_ul": s.qubit_ng_per_ul,
				"nanodrop_ng_per_ul": s.nanodrop_ng_per_ul,
				"a260_a280": s.a260_a280,
				"a260_a230": s.a260_a230,
			}
			for s in samples
		],
	}
	return json.dumps(data, ensure_ascii=False, indent=2)


def samples_to_csv(samples: Iterable[Sample]) -> str:
	buffer = io.StringIO()
	writer = csv.writer(buffer)
	writer.writerow([
		"id","submission_id","row_index","table_index","page_index","name",
		"volume_ul","qubit_ng_per_ul","nanodrop_ng_per_ul","a260_a280","a260_a230",
	])
	for s in samples:
		writer.writerow([
			s.id,
			s.submission_id,
			s.row_index,
			s.table_index,
			s.page_index,
			s.name or "",
			"" if s.volume_ul is None else s.volume_ul,
			"" if s.qubit_ng_per_ul is None else s.qubit_ng_per_ul,
			"" if s.nanodrop_ng_per_ul is None else s.nanodrop_ng_per_ul,
			"" if s.a260_a280 is None else s.a260_a280,
			"" if s.a260_a230 is None else s.a260_a230,
		])
	return buffer.getvalue()


