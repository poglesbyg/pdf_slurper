#!/usr/bin/env python
"""Run the new modular web UI server."""

import uvicorn
from src.presentation.web.server import app
from src.infrastructure.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"Starting PDF Slurper Web UI v2")
    print(f"Environment: {settings.environment}")
    print(f"Web UI: http://{settings.host}:{settings.web_port}")
    print(f"API: http://{settings.host}:{settings.port}/api/v1")
    print(f"Dashboard: http://{settings.host}:{settings.web_port}/")
    print(f"Upload: http://{settings.host}:{settings.web_port}/upload")
    
    uvicorn.run(
        "src.presentation.web.server:app",
        host=settings.host,
        port=settings.web_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.value.lower()
    )
