FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    PDF_SLURPER_DB="/data/db.sqlite3"

WORKDIR /app

# system deps for pdfplumber/pymupdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libfreetype6 \
    libjpeg62-turbo \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel
COPY pyproject.toml ./
COPY uv.lock ./
COPY pdf_slurper ./pdf_slurper
RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["pdf-slurp-web"]


