#!/usr/bin/env python
"""Run both API and Web UI in a single process for production."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.infrastructure.config.settings import get_settings
from src.application.container import init_container, close_container
from src.presentation.api.v1.routers import submissions
from src.shared.exceptions import APIException, BaseException as AppException

# API metadata
API_VERSION = "2.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    init_container(settings)
    yield
    # Shutdown
    close_container()


def create_combined_app() -> FastAPI:
    """Create combined FastAPI application with both API and Web UI."""
    settings = get_settings()
    
    app = FastAPI(
        title="PDF Slurper v2",
        version=API_VERSION,
        description="PDF Slurper - Laboratory Sample Tracking System",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.api_docs_enabled else None,
        redoc_url="/api/redoc" if settings.api_docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Templates for Web UI
    templates_dir = Path(__file__).parent / "src" / "presentation" / "web" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Static files (if any)
    static_dir = Path(__file__).parent / "src" / "presentation" / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Exception handlers
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle API exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.to_dict()}
        )
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application exceptions."""
        return JSONResponse(
            status_code=500,
            content={"error": exc.to_dict()}
        )
    
    # Health check endpoints
    @app.get("/health", tags=["health"])
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "version": API_VERSION}
    
    @app.get("/ready", tags=["health"])
    async def ready():
        """Readiness check endpoint."""
        return {"status": "ready", "version": API_VERSION}
    
    # Serve config.js
    @app.get("/config.js", response_class=HTMLResponse)
    async def serve_config():
        """Serve the config.js file."""
        config_content = """// Local Development Configuration
window.API_CONFIG = {
    getApiUrl: function(path) {
        const baseUrl = 'http://localhost:8080';
        if (!path) return baseUrl;
        const cleanPath = path.startsWith('/') ? path : '/' + path;
        return baseUrl + cleanPath;
    },
    apiBase: '/api/v1'
};

window.config = window.API_CONFIG;
console.log('API Configuration (LOCAL):', window.API_CONFIG.getApiUrl());"""
        return HTMLResponse(content=config_content, media_type="application/javascript")
    
        # API Routes
    app.include_router(
        submissions.router,
        prefix="/api/v1",
        tags=["submissions"]
    )
    
    # Web UI Routes
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Dashboard page."""
        return templates.TemplateResponse("dashboard.html", {"request": request})
    
    @app.get("/upload", response_class=HTMLResponse)
    async def upload_page(request: Request):
        """Upload page."""
        return templates.TemplateResponse("upload.html", {"request": request})
    
    @app.get("/submissions", response_class=HTMLResponse)
    async def submissions_page(request: Request):
        """Submissions page."""
        return templates.TemplateResponse("submissions.html", {"request": request})
    
    @app.get("/submission/{submission_id}", response_class=HTMLResponse)
    async def submission_detail_path(request: Request, submission_id: str):
        """Submission detail page with path parameter."""
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })
    
    @app.get("/submission.html", response_class=HTMLResponse)
    async def submission_detail_query(request: Request):
        """Submission detail page with query parameter."""
        submission_id = request.query_params.get("id", "")
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })
    
    @app.get("/submission_detail.html", response_class=HTMLResponse)
    async def submission_detail_page(request: Request):
        """Submission detail page (alternative URL)."""
        submission_id = request.query_params.get("id", "")
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })
    
    @app.get("/analytics", response_class=HTMLResponse)
    async def analytics_page(request: Request):
        """Analytics page (placeholder)."""
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    @app.get("/dashboard.html", response_class=HTMLResponse)
    async def dashboard_html(request: Request):
        """Dashboard page (HTML extension)."""
        return templates.TemplateResponse("dashboard.html", {"request": request})
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_alt(request: Request):
        """Dashboard page (alternative URL)."""
        return templates.TemplateResponse("dashboard.html", {"request": request})
    
    @app.get("/submissions.html", response_class=HTMLResponse)
    async def submissions_html(request: Request):
        """Submissions page (HTML extension)."""
        return templates.TemplateResponse("submissions.html", {"request": request})
    
    @app.get("/upload.html", response_class=HTMLResponse)
    async def upload_html(request: Request):
        """Upload page (HTML extension)."""
        return templates.TemplateResponse("upload.html", {"request": request})
    
    return app


# Create application instance
app = create_combined_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    print(f"Starting PDF Slurper Combined Server v2")
    print(f"Environment: {settings.environment}")
    print(f"Web UI: http://{settings.host}:{settings.port}/")
    print(f"API: http://{settings.host}:{settings.port}/api/v1")
    print(f"API Docs: http://{settings.host}:{settings.port}/api/docs")
    
    uvicorn.run(
        "start_combined:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.value.lower()
    )
