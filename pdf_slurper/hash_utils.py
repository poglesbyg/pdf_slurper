from __future__ import annotations

import hashlib
from pathlib import Path
import os
from typing import Tuple


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
	sha = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(chunk_size), b""):
			sha.update(chunk)
	return sha.hexdigest()


def file_fingerprint(path: Path) -> Tuple[int, float]:
	"""Return (size_bytes, mtime_epoch)."""
	st = os.stat(path)
	return (st.st_size, st.st_mtime)


