from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
	sha = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(chunk_size), b""):
			sha.update(chunk)
	return sha.hexdigest()


