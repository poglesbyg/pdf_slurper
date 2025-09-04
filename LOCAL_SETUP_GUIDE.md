# 📋 Local Development Setup Guide

This guide will help you run the PDF Slurper application locally for testing and debugging.

## 🚀 Quick Start Options

### Option 1: Using Python Directly (Simplest)

#### Prerequisites
```bash
# Install Python 3.11+ and pip
python3 --version  # Should be 3.11 or higher

# Install dependencies
pip install -r requirements.txt
# OR using uv (faster)
uv pip install -r pyproject.toml
```

#### Run Combined Server (API + Web UI)
```bash
# This runs both API and web UI on port 8080
python start_combined.py
```

Then access:
- Web UI: http://localhost:8080/
- API: http://localhost:8080/api/v1
- API Docs: http://localhost:8080/api/docs

#### Run API and Web UI Separately
```bash
# Terminal 1: Run API server (port 8080)
python run_api.py

# Terminal 2: Run Web UI (port 3000)
python run_web_ui.py
```

### Option 2: Using Docker Compose (Production-like)

```bash
# Build and start services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

Access at:
- API: http://localhost:8080
- Legacy Web (if needed): http://localhost:8000

### Option 3: Simple HTTP Server for Frontend Testing

If you just want to test the frontend with the deployed API:

```bash
# Terminal 1: Run a simple HTTP server for the frontend
cd web-static
python3 -m http.server 8000

# Terminal 2: Run the API locally
python run_api.py
```

Then update `web-static/config.js`:
```javascript
window.API_CONFIG = {
    getApiUrl: function(path) {
        // Point to local API
        return 'http://localhost:8080' + (path ? path : '');
    },
    apiBase: '/api/v1'
};
```

## 🔧 Detailed Setup

### 1. Environment Setup

Create a `.env` file in the project root:
```bash
# Environment
PDF_SLURPER_ENV=development
PDF_SLURPER_HOST=0.0.0.0
PDF_SLURPER_PORT=8080
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=sqlite:///./data/pdf_slurper.db
PDF_SLURPER_DB=./data/pdf_slurper.db

# API Settings
API_DOCS_ENABLED=true
API_CORS_ORIGINS=["*"]

# File Storage
UPLOAD_DIR=./uploads
DATA_DIR=./data
```

### 2. Database Setup

```bash
# Create data directories
mkdir -p data uploads logs

# Initialize database with legacy schema
python -c "
from pdf_slurper.db import init_db, get_engine
engine = get_engine()
init_db(engine)
print('✅ Database initialized')
"

# Run migrations for v2 schema
alembic upgrade head
```

### 3. Test PDF Upload Locally

```bash
# Using curl
curl -X POST http://localhost:8080/api/v1/submissions/ \
  -F "pdf_file=@custom_forms_11095857_1756931956.pdf" \
  -F "storage_location=Test Location" \
  -F "force=false"

# Using Python
python -c "
import requests
with open('custom_forms_11095857_1756931956.pdf', 'rb') as f:
    files = {'pdf_file': f}
    data = {'storage_location': 'Test Location', 'force': 'false'}
    response = requests.post('http://localhost:8080/api/v1/submissions/', files=files, data=data)
    print(response.json())
"
```

## 🐛 Debugging Tips

### Enable Debug Logging
```python
# In run_api.py or start_combined.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Database Content
```bash
# View submissions in database
python -c "
from pdf_slurper.db import Submission, open_session
from sqlmodel import select

with open_session() as session:
    submissions = session.exec(select(Submission)).all()
    for sub in submissions:
        print(f'{sub.id}: {sub.identifier} - {sub.requester}')
"
```

### Test API Endpoints
```bash
# Get all submissions
curl http://localhost:8080/api/v1/submissions/

# Get specific submission
curl http://localhost:8080/api/v1/submissions/sub_06fa0d0e37b7

# Get samples for a submission
curl http://localhost:8080/api/v1/submissions/sub_06fa0d0e37b7/samples
```

### Fix CORS Issues
If you're getting CORS errors, update the API to allow all origins:
```python
# In src/infrastructure/config/settings.py
API_CORS_ORIGINS = ["*"]  # Allow all origins for local testing
```

## 📁 Project Structure for Local Development

```
pdf_slurper/
├── data/               # Local database files
│   └── pdf_slurper.db
├── uploads/            # Uploaded PDF files
├── logs/               # Application logs
├── web-static/         # Static frontend files
│   ├── dashboard.html
│   ├── upload.html
│   └── config.js      # Update API URL here
└── src/                # Application source code
    ├── presentation/   # API and Web UI
    ├── domain/         # Business logic
    └── infrastructure/ # Database, PDF processing
```

## 🔍 Common Issues and Solutions

### Issue: "No such table" errors
**Solution:** Initialize the database:
```bash
python -c "from pdf_slurper.db import init_db, get_engine; init_db(get_engine())"
```

### Issue: PDF not processing
**Solution:** Check if PyMuPDF is installed:
```bash
pip install pymupdf pdfplumber
```

### Issue: Frontend not showing data
**Solution:** Check API is running and CORS is enabled:
```bash
# Test API is accessible
curl http://localhost:8080/health

# Check CORS headers
curl -I -X OPTIONS http://localhost:8080/api/v1/submissions/
```

### Issue: File upload fails
**Solution:** Ensure upload directory exists and is writable:
```bash
mkdir -p uploads
chmod 755 uploads
```

## 🎯 Quick Test Workflow

1. **Start the server:**
   ```bash
   python start_combined.py
   ```

2. **Upload a test PDF:**
   - Go to http://localhost:8080/upload
   - Select the test PDF file
   - Enter storage location
   - Click Upload

3. **View the results:**
   - Dashboard: http://localhost:8080/
   - Submission details: Click on any submission
   - API response: http://localhost:8080/api/v1/submissions/

4. **Debug if needed:**
   - Check console logs in terminal
   - Check browser console (F12)
   - Check API docs: http://localhost:8080/api/docs

## 🔧 Advanced: VSCode Debugging

Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug PDF Slurper",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/start_combined.py",
            "console": "integratedTerminal",
            "env": {
                "PDF_SLURPER_ENV": "development",
                "LOG_LEVEL": "DEBUG"
            }
        }
    ]
}
```

Then press F5 in VSCode to start debugging with breakpoints!

## ✅ Success Indicators

When running locally, you should see:
- ✅ Server starts on http://localhost:8080
- ✅ Can access dashboard without errors
- ✅ Can upload PDF files
- ✅ Can view submission details
- ✅ API returns data at /api/v1/submissions/
- ✅ No CORS errors in browser console

Happy debugging! 🎉
