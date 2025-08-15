from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, PackageLoader, select_autoescape
from sqlmodel import select

from .db import (
	DEFAULT_DB_PATH,
	Submission,
	Sample,
	init_db,
	open_session,
	list_submissions,
	delete_submission,
)
from .exporters import submission_to_json, samples_to_csv
from .slurp import slurp_pdf


env = Environment(loader=PackageLoader("pdf_slurper", "templates"), autoescape=select_autoescape())

app = FastAPI(title="PDF Slurper")
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    # Try a trivial DB operation
    try:
        with open_session(DEFAULT_DB_PATH) as session:
            _ = session.exec(select(Submission).limit(1)).first()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="not ready")


@app.get("/", response_class=HTMLResponse)
def home():
	submissions = []
	with open_session(DEFAULT_DB_PATH) as session:
		submissions = list_submissions(session, limit=100)
	template = env.get_template("index.html")
	return template.render(submissions=submissions)


@app.get("/submission/{submission_id}", response_class=HTMLResponse)
def view_submission(submission_id: str):
	with open_session(DEFAULT_DB_PATH) as session:
		sub = session.get(Submission, submission_id)
		if not sub:
			raise HTTPException(status_code=404, detail="Not found")
		samples = list(session.exec(select(Sample).where(Sample.submission_id == sub.id)))
		
		# Get statistics
		from .db import get_submission_statistics
		stats = get_submission_statistics(session, submission_id)
		
		# Use enhanced template if available
		try:
			template = env.get_template("submission_enhanced.html")
		except:
			template = env.get_template("submission.html")
		
		return template.render(submission=sub, samples=samples, stats=stats)


@app.post("/upload", response_class=HTMLResponse)
async def upload(file: UploadFile = File(...)):
	init_db(DEFAULT_DB_PATH)
	tmp_path = Path("/tmp") / file.filename
	content = await file.read()
	tmp_path.write_bytes(content)
	result = slurp_pdf(tmp_path, db_path=DEFAULT_DB_PATH)
	template = env.get_template("uploaded.html")
	return template.render(submission_id=result.submission_id, num_samples=result.num_samples)


@app.get("/submission/{submission_id}/json")
def export_json(submission_id: str):
	with open_session(DEFAULT_DB_PATH) as session:
		sub = session.get(Submission, submission_id)
		if not sub:
			raise HTTPException(status_code=404, detail="Not found")
		samples = list(session.exec(select(Sample).where(Sample.submission_id == sub.id)))
		return Response(content=submission_to_json(sub, samples), media_type="application/json")


@app.get("/submission/{submission_id}/csv")
def export_csv(submission_id: str):
	with open_session(DEFAULT_DB_PATH) as session:
		sub = session.get(Submission, submission_id)
		if not sub:
			raise HTTPException(status_code=404, detail="Not found")
		samples = list(session.exec(select(Sample).where(Sample.submission_id == sub.id)))
		return PlainTextResponse(samples_to_csv(samples), media_type="text/csv")


@app.post("/submission/{submission_id}/delete")
def delete(submission_id: str):
	with open_session(DEFAULT_DB_PATH) as session:
		ok = delete_submission(session, submission_id)
		if not ok:
			raise HTTPException(status_code=404, detail="Not found")
	return {"status": "ok"}


@app.post("/submission/{submission_id}/apply-qc")
def apply_qc_endpoint(
	submission_id: str,
	min_concentration: float = 10.0,
	min_volume: float = 20.0,
	min_ratio: float = 1.8
):
	"""Apply QC thresholds to all samples in a submission"""
	with open_session(DEFAULT_DB_PATH) as session:
		from .db import apply_qc_thresholds
		flagged = apply_qc_thresholds(session, submission_id, min_concentration, min_volume, min_ratio)
		return {"flagged": flagged, "status": "ok"}


@app.post("/submission/{submission_id}/batch-update")
def batch_update_endpoint(
	submission_id: str,
	sample_ids: list[str],
	status: str,
	processed_by: Optional[str] = None
):
	"""Batch update sample status"""
	with open_session(DEFAULT_DB_PATH) as session:
		from .db import batch_update_sample_status
		count = batch_update_sample_status(session, sample_ids, status, processed_by)
		return {"updated": count, "status": "ok"}


@app.get("/submission/{submission_id}/manifest")
def generate_manifest_endpoint(submission_id: str):
	"""Generate a CSV manifest for all samples"""
	with open_session(DEFAULT_DB_PATH) as session:
		samples = list(session.exec(select(Sample).where(Sample.submission_id == submission_id)))
		
		import csv
		import io
		buffer = io.StringIO()
		writer = csv.writer(buffer)
		
		# Header
		writer.writerow([
			"Sample_ID", "Name", "Barcode", "Status", "Location",
			"Volume_uL", "Conc_ng_uL", "A260_A280", "QC_Status",
			"Quality_Score", "QC_Notes"
		])
		
		# Data
		for s in samples:
			writer.writerow([
				s.id,
				s.name or "",
				s.barcode or "",
				s.status or "received",
				s.location or "",
				s.volume_ul or "",
				s.qubit_ng_per_ul or s.nanodrop_ng_per_ul or "",
				s.a260_a280 or "",
				s.qc_status or "pending",
				f"{s.quality_score:.1f}" if s.quality_score else "",
				s.qc_notes or "",
			])
		
		return PlainTextResponse(
			buffer.getvalue(),
			media_type="text/csv",
			headers={"Content-Disposition": f"attachment; filename=manifest_{submission_id}.csv"}
		)


@app.get("/sample/{sample_id}/edit", response_class=HTMLResponse)
def edit_sample_page(sample_id: str):
	"""Show sample edit form"""
	with open_session(DEFAULT_DB_PATH) as session:
		sample = session.get(Sample, sample_id)
		if not sample:
			raise HTTPException(status_code=404, detail="Sample not found")
		
		# Simple edit form (you can create a proper template later)
		html = f"""
		<html>
		<head><title>Edit Sample {sample_id}</title></head>
		<body style="font-family: sans-serif; padding: 2rem;">
			<h1>Edit Sample: {sample.name or sample_id}</h1>
			<form method="post" action="/sample/{sample_id}/update">
				<div style="margin: 1rem 0;">
					<label>Status:</label><br>
					<select name="status">
						<option value="received" {'selected' if sample.status == 'received' else ''}>Received</option>
						<option value="processing" {'selected' if sample.status == 'processing' else ''}>Processing</option>
						<option value="sequenced" {'selected' if sample.status == 'sequenced' else ''}>Sequenced</option>
						<option value="completed" {'selected' if sample.status == 'completed' else ''}>Completed</option>
						<option value="failed" {'selected' if sample.status == 'failed' else ''}>Failed</option>
					</select>
				</div>
				<div style="margin: 1rem 0;">
					<label>Location:</label><br>
					<input type="text" name="location" value="{sample.location or ''}" placeholder="e.g., Freezer-A Shelf-3">
				</div>
				<div style="margin: 1rem 0;">
					<label>Barcode:</label><br>
					<input type="text" name="barcode" value="{sample.barcode or ''}">
				</div>
				<div style="margin: 1rem 0;">
					<label>Notes:</label><br>
					<textarea name="notes" rows="4" cols="50">{sample.notes or ''}</textarea>
				</div>
				<button type="submit">Save Changes</button>
				<a href="/submission/{sample.submission_id}">Cancel</a>
			</form>
		</body>
		</html>
		"""
		return HTMLResponse(html)


@app.post("/sample/{sample_id}/update")
async def update_sample_endpoint(
	sample_id: str,
	status: str = Form(None),
	location: str = Form(None),
	barcode: str = Form(None),
	notes: str = Form(None)
):
	"""Update sample fields"""
	with open_session(DEFAULT_DB_PATH) as session:
		sample = session.get(Sample, sample_id)
		if not sample:
			raise HTTPException(status_code=404, detail="Sample not found")
		
		if status:
			sample.status = status
		if location is not None:
			sample.location = location
		if barcode is not None:
			sample.barcode = barcode
		if notes is not None:
			sample.notes = notes
		
		from datetime import datetime
		sample.updated_at = datetime.utcnow()
		session.add(sample)
		session.commit()
		
		# Redirect back to submission view
		from fastapi.responses import RedirectResponse
		return RedirectResponse(f"/submission/{sample.submission_id}", status_code=302)


def main():
    import os
    import uvicorn
    init_db(DEFAULT_DB_PATH)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("pdf_slurper.server:app", host=host, port=port, reload=False)


@app.get("/favicon.ico")
def favicon():
	# 1x1 transparent gif
	data = (
		b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
	)
	return Response(content=data, media_type="image/gif")


