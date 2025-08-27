# Tailwind CSS Production Setup

## Current Setup (Development)
Currently, the application uses Tailwind CSS via CDN for development convenience. This is shown with a warning in the browser console.

## Production Setup

To use Tailwind CSS in production, follow these steps:

### 1. Install Dependencies
```bash
npm install
```

### 2. Build CSS for Production
```bash
npm run build-css
```

This will generate a minified CSS file at `static/css/styles.css`.

### 3. Update Templates
Replace the CDN script tag in `src/presentation/web/templates/base.html`:

```html
<!-- Replace this: -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- With this: -->
<link rel="stylesheet" href="/static/css/styles.css">
```

### 4. Serve Static Files
Ensure your web server (nginx, FastAPI static files, etc.) is configured to serve the `/static` directory.

For FastAPI, add:
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

### 5. Development Workflow
For development with hot-reload:
```bash
npm run dev
```

This watches for changes in templates and rebuilds CSS automatically.

## Docker Production Build
Add to your Dockerfile:
```dockerfile
# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Copy package files
COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY src/input.css ./src/

# Install and build CSS
RUN npm ci --only=production
RUN npm run build-css
```

## Benefits
- **Smaller file size**: Only includes used CSS classes
- **Better performance**: No runtime CSS generation
- **Production-ready**: No browser console warnings
- **Customizable**: Full control over Tailwind configuration
