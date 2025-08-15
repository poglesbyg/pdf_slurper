#!/usr/bin/env python
"""Run the modular API server."""

import uvicorn
from src.presentation.api.app import app
from src.infrastructure.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"Starting PDF Slurper API v2")
    print(f"Environment: {settings.environment}")
    print(f"API Docs: http://{settings.host}:{settings.port}/api/docs")
    print(f"OpenAPI: http://{settings.host}:{settings.port}/api/openapi.json")
    
    uvicorn.run(
        "src.presentation.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.value.lower()
    )
