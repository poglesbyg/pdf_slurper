# PDF Slurper

A uv-based Python tool and web app for extracting ("slurping") structured data from laboratory PDFs into a SQLite database. It focuses on submissions and sample tables, normalizes headers, parses numeric fields, and exports data as JSON/CSV.

## Features

- CLI and web UI
- PDF metadata and text extraction (PyMuPDF)
- Table extraction (pdfplumber) with header normalization and numeric parsing
- Submission + Sample schema in SQLite (SQLModel/SQLAlchemy 2)
- Idempotency by content hash; records file size and mtime
- JSON and CSV export; NDJSON option for large sample sets
- Lightweight DB migrations on startup
- Dockerfile and OpenShift deployment steps

## Requirements

- Python 3.13 (managed by uv)
- macOS/Linux
- Optional: Docker, OpenShift CLI (`oc`) for deployment

## Quick start (CLI)

```bash
cd /Users/paulgreenwood/Dev/20250814/pdf_slurper
uv sync
uv run pdf-slurp db-init
uv run pdf-slurp info "/Users/paulgreenwood/Dev/20250814/HTSF--JL-147_quote_160217072025.pdf"
uv run pdf-slurp tables "/Users/paulgreenwood/Dev/20250814/HTSF--JL-147_quote_160217072025.pdf" --pages "1-2" --output -
uv run pdf-slurp slurp "/Users/paulgreenwood/Dev/20250814/HTSF--JL-147_quote_160217072025.pdf"
uv run pdf-slurp list-submissions
uv run pdf-slurp show-submission <submission_id>
uv run pdf-slurp list-samples <submission_id> --limit 20
uv run pdf-slurp export <submission_id> --fmt json --output -
uv run pdf-slurp export <submission_id> --fmt json --ndjson --output -
uv run pdf-slurp export <submission_id> --fmt csv --output samples.csv
uv run pdf-slurp delete-submission <submission_id>
```

Notes:
- Run commands from the project directory so console entry points resolve.
- Pages are 1-based; page ranges accept `1,3-5` syntax.

## Web server

```bash
cd /Users/paulgreenwood/Dev/20250814/pdf_slurper
uv run pdf-slurp-web
# open http://127.0.0.1:8000
```

Web features:
- Upload PDF, create a submission
- List submissions with links to detail pages
- View parsed metadata and samples
- Export JSON/CSV
- Delete submission

## Configuration

- `PDF_SLURPER_DB` (path): SQLite file path. Default: `~/.pdf_slurper/db.sqlite3` (Docker default: `/data/db.sqlite3`).
- `HOST` (string): Bind host. Default: `0.0.0.0` for container, `127.0.0.1` locally.
- `PORT` (int): Bind port. Default: `8080` for container, `8000` when run locally.

## Data model

Submission (key fields):
- `id` (str)
- `created_at` (UTC)
- `source_file`, `source_sha256`, `source_size?`, `source_mtime?`
- PDF metadata: `title`, `author`, `subject`, `creator`, `producer`, `creation_date`, `page_count`
- Slurped form metadata (examples): `identifier`, `as_of`, `expires_on`, `service_requested`, `requester`, `requester_email`, `lab`, `billing_address`, `pis`, `financial_contacts`, `request_summary`, `forms_text`, `will_submit_dna_for_json`, `type_of_sample_json`, `human_dna`, `source_organism`, `sample_buffer_json`

Sample:
- `id`, `submission_id`
- `row_index`, `table_index`, `page_index`
- `name`, `volume_ul`, `qubit_ng_per_ul`, `nanodrop_ng_per_ul`, `a260_a280`, `a260_a230`

## Idempotency

- First slurp of a file creates a submission keyed by SHA-256.
- Re-slurping same content updates submission metadata and avoids duplicate samples.
- File size and mtime are also stored for fast fingerprinting.

## Export formats

- JSON: submission + samples in a single document (pretty-printed). NDJSON optional for line-by-line samples.
- CSV: header row, one sample per line.

## Development

```bash
cd /Users/paulgreenwood/Dev/20250814/pdf_slurper
uv sync
# examples
uv run pdf-slurp list-submissions
```

Recommended (future):
- Pre-commit (black, ruff, isort, mypy)
- Tests (pytest): unit tests for mapping and parsing, integration for CLI/web
- Alembic migrations

## Docker

```bash
cd /Users/paulgreenwood/Dev/20250814/pdf_slurper
docker build -t pdf-slurper:local .
docker run --rm -p 8080:8080 \
  -e PORT=8080 -e HOST=0.0.0.0 \
  -e PDF_SLURPER_DB=/data/db.sqlite3 \
  -v $(pwd)/.data:/data pdf-slurper:local
# open http://127.0.0.1:8080
```

## OpenShift (example)

```bash
oc project <your-project>
oc new-build --name=pdf-slurper --binary --strategy=docker
oc start-build pdf-slurper --from-dir=. --follow
oc new-app --image-stream=pdf-slurper:latest --name=pdf-slurper
oc set env deployment/pdf-slurper PDF_SLURPER_DB=/data/db.sqlite3 HOST=0.0.0.0 PORT=8080
oc set volume deployment/pdf-slurper --add --name=data --type pvc --claim-size=1Gi --mount-path=/data
oc expose service pdf-slurper
oc get route pdf-slurper -o jsonpath='{.spec.host}'
```

## Roadmap (excerpt)

- Parsing: finalize facility-specific mappings, improve block extraction, validations
- Data: move to Alembic, add indexes
- CLI/web: filters, inline edits, auth
- Deployment: probes, limits, TLS, CI
- Optional PyTorch mode: OCR fallback, layout/table detection, key–value extraction

## License

Add your license here.


