#!/bin/bash

# PDF Slurper Local Setup Script
# This script sets up and runs the PDF Slurper application locally

set -e

echo "🚀 PDF Slurper Local Setup"
echo "=========================="

# Check Python version
echo "Checking Python version..."
if ! python3 --version | grep -E "3\.(11|12)" > /dev/null; then
    echo "❌ Python 3.11+ is required"
    exit 1
fi
echo "✅ Python version OK"

# Create necessary directories
echo "Creating directories..."
mkdir -p data uploads logs
echo "✅ Directories created"

# Install dependencies
echo "Installing dependencies..."
if command -v uv &> /dev/null; then
    echo "Using uv to install dependencies..."
    uv pip install -r pyproject.toml
else
    echo "Using pip to install dependencies..."
    pip3 install -r pyproject.toml || pip3 install fastapi sqlmodel uvicorn pdfplumber pymupdf python-multipart jinja2 python-dotenv
fi
echo "✅ Dependencies installed"

# Initialize database
echo "Initializing database..."
python3 -c "
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path.cwd()))

try:
    from pdf_slurper.db import init_db, get_engine
    engine = get_engine(Path('./data/pdf_slurper.db'))
    init_db(engine)
    print('✅ Legacy database initialized')
except Exception as e:
    print(f'⚠️  Legacy database init failed (may already exist): {e}')

try:
    from src.infrastructure.persistence.database import init_database
    init_database()
    print('✅ V2 database initialized')
except Exception as e:
    print(f'⚠️  V2 database init failed (may already exist): {e}')
"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Environment
PDF_SLURPER_ENV=development
PDF_SLURPER_HOST=0.0.0.0
PDF_SLURPER_PORT=8080
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./data/pdf_slurper.db
PDF_SLURPER_DB=./data/pdf_slurper.db

# API Settings
API_DOCS_ENABLED=true
API_CORS_ORIGINS=["*"]

# File Storage
UPLOAD_DIR=./uploads
DATA_DIR=./data
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Update web-static config for local development
echo "Updating frontend config..."
cat > web-static/config.js << 'EOF'
// Local Development Configuration
window.API_CONFIG = {
    getApiUrl: function(path) {
        // Use localhost for local development
        const baseUrl = 'http://localhost:8080';
        if (!path) return baseUrl;
        const cleanPath = path.startsWith('/') ? path : '/' + path;
        return baseUrl + cleanPath;
    },
    apiBase: '/api/v1'
};

// For backward compatibility
window.config = window.API_CONFIG;

console.log('API Configuration loaded (LOCAL):', window.API_CONFIG.getApiUrl());
EOF
echo "✅ Frontend config updated for local development"

# Copy web-static files to src/presentation/web/templates for the combined server
echo "Copying web files..."
mkdir -p src/presentation/web/templates
cp -f web-static/*.html src/presentation/web/templates/ 2>/dev/null || true
echo "✅ Web files copied"

echo ""
echo "==============================================="
echo "✅ Setup complete!"
echo "==============================================="
echo ""
echo "To start the server, run ONE of these options:"
echo ""
echo "Option 1: Combined server (recommended):"
echo "  python3 start_combined.py"
echo ""
echo "Option 2: API only:"
echo "  python3 run_api.py"
echo ""
echo "Option 3: Separate terminals:"
echo "  Terminal 1: python3 run_api.py"
echo "  Terminal 2: cd web-static && python3 -m http.server 8000"
echo ""
echo "Then access:"
echo "  Web UI: http://localhost:8080/"
echo "  API: http://localhost:8080/api/v1"
echo "  API Docs: http://localhost:8080/api/docs"
echo ""
echo "Test PDF upload:"
echo "  1. Go to http://localhost:8080/upload"
echo "  2. Upload: custom_forms_11095857_1756931956.pdf"
echo "  3. View at: http://localhost:8080/"
echo ""
