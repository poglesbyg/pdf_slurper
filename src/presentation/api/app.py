"""FastAPI application with versioned API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from ...infrastructure.config.settings import get_settings
from ...application.container import init_container, close_container
from ...shared.exceptions import APIException, BaseException as AppException
from .v1.routers import submissions

# API metadata
API_TITLE = "PDF Slurper API"
API_VERSION = "2.0.0"
API_DESCRIPTION = """
## PDF Slurper - Laboratory Sample Tracking System

A professional PDF data extraction and sample tracking system for genetic laboratories.

### Features

* **PDF Processing** - Extract structured data from laboratory PDFs
* **Sample Tracking** - Track samples through workflow stages
* **Quality Control** - Apply QC thresholds and scoring
* **Batch Operations** - Update multiple samples at once
* **Search & Filter** - Find submissions and samples quickly

### API Versioning

This API uses URL versioning. Current version: `v1`

All endpoints are prefixed with `/api/v1`

### Authentication

Authentication is currently not required for development.
Production deployments should implement OAuth2 or API keys.

### Rate Limiting

Rate limits may apply in production:
- 100 requests per minute per IP
- 1000 requests per hour per API key

### Response Format

All responses follow a consistent format:

**Success Response:**
```json
{
    "data": {...},
    "meta": {
        "version": "v1",
        "timestamp": "2024-01-01T00:00:00Z"
    }
}
```

**Error Response:**
```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": {...}
    }
}
```

### Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created
- `204 No Content` - Resource deleted
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily down
"""

TAGS_METADATA = [
    {
        "name": "submissions",
        "description": "Operations with submissions and samples",
        "externalDocs": {
            "description": "Domain documentation",
            "url": "https://github.com/yourusername/pdf-slurper/docs/",
        },
    },
    {
        "name": "samples",
        "description": "Operations with individual samples",
    },
    {
        "name": "health",
        "description": "Health check endpoints",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    init_container(settings)
    yield
    # Shutdown
    close_container()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.api_docs_enabled else None,
        redoc_url="/api/redoc" if settings.api_docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
        openapi_tags=TAGS_METADATA,
        servers=[
            {"url": "/", "description": "Current server"},
            {"url": "http://localhost:8080", "description": "Local development"},
            {"url": "https://api.example.com", "description": "Production"},
        ],
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle API exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.to_dict()
            }
        )
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application exceptions."""
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.to_dict()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {"type": type(exc).__name__}
                }
            }
        )
    
    # Health check endpoints
    @app.get(
        "/health",
        tags=["health"],
        summary="Health check",
        description="Basic health check endpoint"
    )
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "version": API_VERSION}
    
    @app.get(
        "/ready",
        tags=["health"],
        summary="Readiness check",
        description="Check if service is ready to handle requests"
    )
    async def ready():
        """Readiness check endpoint."""
        # Could check database connection, etc.
        return {"status": "ready", "version": API_VERSION}
    
    # Include routers
    app.include_router(
        submissions.router,
        prefix="/api/v1",
        tags=["submissions"]
    )
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=API_TITLE,
            version=API_VERSION,
            description=API_DESCRIPTION,
            routes=app.routes,
            tags=TAGS_METADATA,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT authentication token"
            },
            "apiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key authentication"
            }
        }
        
        # Add examples
        openapi_schema["components"]["examples"] = {
            "SubmissionExample": {
                "value": {
                    "id": "sub_123abc",
                    "created_at": "2024-01-01T00:00:00Z",
                    "sample_count": 96,
                    "metadata": {
                        "identifier": "HTSF-001",
                        "requester": "John Doe",
                        "lab": "Genetics Lab"
                    }
                }
            },
            "ErrorExample": {
                "value": {
                    "error": {
                        "code": "SUBMISSION_NOT_FOUND",
                        "message": "Submission not found: sub_123",
                        "details": {}
                    }
                }
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app


# Create application instance
app = create_app()
