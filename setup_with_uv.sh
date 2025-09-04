#!/bin/bash

# PDF Slurper Local Setup with UV
# Fast setup using the UV package manager

set -e

echo "🚀 PDF Slurper Setup with UV"
echo "============================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

echo "✅ UV is ready"
uv --version

# Create virtual environment with uv
echo ""
echo "Creating virtual environment..."
uv venv --python 3.11 2>/dev/null || uv venv
echo "✅ Virtual environment created"

# Activate virtual environment
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""

# Install dependencies with uv
echo "Installing dependencies with UV..."
source .venv/bin/activate 2>/dev/null || true

uv pip install \
    fastapi \
    uvicorn[standard] \
    sqlmodel \
    pdfplumber \
    pymupdf \
    python-multipart \
    jinja2 \
    python-dotenv \
    httpx \
    pydantic \
    pydantic-settings \
    alembic \
    pytest \
    pytest-asyncio \
    aiofiles \
    click

echo "✅ Dependencies installed"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data uploads logs src/presentation/web/templates
echo "✅ Directories created"

# Initialize databases
echo ""
echo "Initializing databases..."
python3 << 'EOF'
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path.cwd()))

# Initialize legacy database
try:
    from pdf_slurper.db import init_db, get_engine, migrate_db
    db_path = Path('./data/pdf_slurper.db')
    engine = get_engine(db_path)
    init_db(engine)
    migrate_db(db_path)  # Add missing columns
    print('✅ Legacy database initialized')
except Exception as e:
    print(f'⚠️  Legacy database: {e}')

# Initialize v2 database
try:
    from src.infrastructure.persistence.database import init_database
    init_database()
    print('✅ V2 database initialized')
except Exception as e:
    print(f'⚠️  V2 database: {e}')
    
print('✅ Databases ready')
EOF

# Create .env file
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cat > .env << 'EOF'
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
fi

# Update frontend config for local development
echo ""
echo "Configuring frontend..."
cat > web-static/config.js << 'EOF'
// Local Development Configuration
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
console.log('API Configuration (LOCAL):', window.API_CONFIG.getApiUrl());
EOF

# Copy HTML files to templates
cp -f web-static/*.html src/presentation/web/templates/ 2>/dev/null || true
echo "✅ Frontend configured"

# Create a quick start script
cat > start_local.sh << 'EOF'
#!/bin/bash
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
echo "Starting PDF Slurper..."
python3 start_combined.py
EOF
chmod +x start_local.sh

echo ""
echo "==============================================="
echo "✅ Setup Complete with UV!"
echo "==============================================="
echo ""
echo "To start the application:"
echo ""
echo "  Option 1: Quick start"
echo "    ./start_local.sh"
echo ""
echo "  Option 2: Manual"
echo "    source .venv/bin/activate"
echo "    python3 start_combined.py"
echo ""
echo "Then open: http://localhost:8080/"
echo ""
echo "Test commands:"
echo "  python3 test_local_setup.py    # Run tests"
echo "  uv pip list                    # Show installed packages"
echo "  deactivate                     # Exit virtual environment"
echo ""