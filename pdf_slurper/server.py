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
		template = env.get_template("submission.html")
		return template.render(submission=sub, samples=samples)


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


