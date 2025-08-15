"""FastAPI web server for the new modular web UI."""

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ...infrastructure.config.settings import get_settings
from ...application.container import Container, init_container, close_container

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="PDF Slurper Web UI",
    description="Modern web interface for PDF Slurper v2",
    version="2.0.0",
    docs_url=None,  # Disable API docs for web UI
    redoc_url=None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Static files (if any)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Container for dependency injection
container: Optional[Container] = None


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global container
    init_container(settings)
    container = Container(settings)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    close_container()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Serve the upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/submissions", response_class=HTMLResponse)
async def submissions_page(request: Request):
    """Serve the submissions list page."""
    return templates.TemplateResponse("submissions.html", {"request": request})


@app.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_detail(request: Request, submission_id: str):
    """Serve the submission detail page."""
    return templates.TemplateResponse("submission_detail.html", {
        "request": request,
        "submission_id": submission_id
    })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Serve the analytics page."""
    return templates.TemplateResponse("analytics.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "web-ui", "version": "2.0.0"}


@app.get("/ready")
async def ready_check():
    """Readiness check endpoint."""
    return {"status": "ready", "service": "web-ui", "version": "2.0.0"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors."""
    return templates.TemplateResponse("404.html", {
        "request": request,
        "message": "Page not found"
    }, status_code=404)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors."""
    return templates.TemplateResponse("500.html", {
        "request": request,
        "message": "Internal server error"
    }, status_code=500)


def main():
    """Run the web server."""
    print(f"Starting PDF Slurper Web UI v2")
    print(f"Environment: {settings.environment}")
    print(f"Web UI: http://{settings.host}:{settings.web_port}")
    print(f"API: http://{settings.host}:{settings.port}/api/v1")
    
    uvicorn.run(
        "src.presentation.web.server:app",
        host=settings.host,
        port=settings.web_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.value.lower()
    )


if __name__ == "__main__":
    main()
