from __future__ import annotations

from typing import Dict, List, Optional


def normalize_header_token(token: str) -> str:
	text = (token or "").strip().lower()
	# unify unicode micro sign and greek mu to 'u'
	text = text.replace("µ", "u").replace("μ", "u")
	# collapse multiple spaces
	text = " ".join(text.split())
	# remove dots
	text = text.replace(".", "")
	return text


def header_to_normalized_list(header_row: List[str]) -> List[str]:
	return [normalize_header_token(h) for h in header_row]


def fuzzy_find(header_norm: List[str], names: List[str]) -> Optional[int]:
	for i, h in enumerate(header_norm):
		for name in names:
			if name in h:
				return i
	return None


def derive_sample_mapping(header_row: List[str]) -> Dict[str, Optional[int]]:
	"""Return a mapping from logical fields to column indices for a table header.

	Keys: name, volume_ul, qubit_ng_per_ul, nanodrop_ng_per_ul, a260_a280, a260_a230
	Values: column index or None if not present.
	"""
	H = header_to_normalized_list(header_row)

	# Known HTSF Nanopore DNA header variants
	# e.g. ["sample name", "volume (ul)", "qubit conc (ng/ul)", "nanodrop conc (ng/ul)", "a260/a280 ratio", "a260/a230 ratio"]
	mapping = {
		"name": fuzzy_find(H, ["sample name", "name", "sample"]),
		"volume_ul": fuzzy_find(H, ["volume (ul)", "volume", "vol"]),
		"qubit_ng_per_ul": fuzzy_find(H, ["qubit conc", "qubit"]),
		"nanodrop_ng_per_ul": fuzzy_find(H, ["nanodrop conc", "nanodrop"]),
		"a260_a280": fuzzy_find(H, ["a260/a280", "260/280", "260 280", "a /a"]),
		"a260_a230": fuzzy_find(H, ["a260/a230", "260/230", "260 230"]),
	}
	return mapping


