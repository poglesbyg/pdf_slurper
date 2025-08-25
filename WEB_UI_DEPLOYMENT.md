# PDF Slurper Web UI Container Deployment

## Architecture

The application is now split into two separate containers:

1. **API Container** - Runs the FastAPI backend (port 8080)
2. **Web UI Container** - Nginx serving static HTML files (port 8080)

The Web UI container uses nginx to:
- Serve static HTML files at `/`
- Proxy API requests from `/api/*` to the API container

## Files Created

### Web UI Files
- `web-static/dashboard.html` - Main dashboard with statistics
- `web-static/upload.html` - PDF upload interface  
- `web-static/submissions.html` - Submissions listing with filtering
- `nginx/nginx.conf` - Nginx configuration for routing
- `Dockerfile.web` - Container definition for web UI
- `openshift/deployment-combined.yaml` - Combined deployment manifest

### Build Scripts
- `scripts/build-web-ui.sh` - Build and deploy web UI container

## Quick Deployment

### Option 1: Use Pre-Built Images (Fastest)

```bash
# Deploy both API and Web UI
oc apply -f openshift/deployment-combined.yaml

# Wait for pods to be ready
oc get pods -l app=pdf-slurper --watch

# Get the URL
oc get route pdf-slurper
```

### Option 2: Build From Source

```bash
# 1. Build API image
oc new-build --name=pdf-slurper-api \
  --binary \
  --strategy=docker \
  --dockerfile-path=Dockerfile.v2

oc start-build pdf-slurper-api --from-dir=. --follow

# 2. Build Web UI image
oc new-build --name=pdf-slurper-web \
  --binary \
  --strategy=docker \
  --dockerfile-path=Dockerfile.web

oc start-build pdf-slurper-web --from-dir=. --follow

# 3. Deploy both
oc apply -f openshift/deployment-combined.yaml

# 4. Check status
oc get pods -l app=pdf-slurper
```

### Option 3: Using the Build Script

```bash
cd scripts
./build-web-ui.sh pdf-slurper
```

## Manual Build and Test Locally

### Build Images Locally

```bash
# Build API image
docker build -f Dockerfile.v2 -t pdf-slurper-api:latest .

# Build Web UI image  
docker build -f Dockerfile.web -t pdf-slurper-web:latest .
```

### Run Locally with Docker Compose

Create a `docker-compose.local.yml`:

```yaml
version: '3.8'
services:
  api:
    image: pdf-slurper-api:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=sqlite:////tmp/data/pdf_slurper.db
    volumes:
      - ./data:/tmp/data
      - ./uploads:/app/uploads

  web:
    image: pdf-slurper-web:latest
    ports:
      - "3000:8080"
    depends_on:
      - api
```

Run:
```bash
docker-compose -f docker-compose.local.yml up
```

Access at: http://localhost:3000

## Architecture Details

### Web UI Container
- **Base Image**: nginx:alpine-slim
- **Memory**: 32-64Mi
- **CPU**: 60-100m
- **Port**: 8080
- **Health Check**: `/dashboard.html`

### API Container
- **Base Image**: python:3.11-slim
- **Memory**: 64-128Mi
- **CPU**: 60-200m
- **Port**: 8080
- **Health Check**: `/health`

### Request Flow
1. User accesses https://pdf-slurper.example.com
2. Route directs to Web UI Service (nginx)
3. Static HTML/JS/CSS served directly
4. API calls (`/api/*`) proxied to API Service
5. API processes requests and returns JSON

## Troubleshooting

### Check Pod Status
```bash
# View all pods
oc get pods -l app=pdf-slurper

# Check API logs
oc logs deployment/pdf-slurper-v2

# Check Web UI logs
oc logs deployment/pdf-slurper-web

# Describe pods for events
oc describe pod -l app=pdf-slurper
```

### Test Services
```bash
# Test API directly
oc port-forward service/pdf-slurper-v2 8080:8080
curl http://localhost:8080/health

# Test Web UI directly  
oc port-forward service/pdf-slurper-web 3000:8080
open http://localhost:3000
```

### Common Issues

#### 1. Web UI Can't Connect to API
- Check that both services are running
- Verify service names match nginx config
- Check network policies if enabled

#### 2. 404 Errors on Web UI
- Ensure HTML files are copied correctly in build
- Check nginx logs for path issues
- Verify nginx.conf is loaded

#### 3. Resource Quota Issues
- Both containers use minimal resources
- Total: ~96Mi memory, 120m CPU minimum
- Adjust limits in deployment if needed

#### 4. Build Failures
- Ensure you're in the project root directory
- Check that all required files exist
- Verify OpenShift has access to base images

## Production Optimizations

### 1. Replace Tailwind CDN
Build Tailwind CSS locally:
```bash
npm install -D tailwindcss
npx tailwindcss -i ./src/input.css -o ./web-static/styles.css --minify
```

### 2. Add Caching Headers
Already configured in nginx.conf for static assets

### 3. Enable Compression
Gzip enabled in nginx.conf

### 4. Use External Database
Replace SQLite with PostgreSQL:
```yaml
DATABASE_URL: "postgresql://user:pass@postgres-service:5432/pdfslurper"
```

### 5. Add Monitoring
- Add Prometheus metrics endpoint
- Configure alerts for pod restarts
- Monitor response times

## Security Considerations

1. **Network Policies**: Restrict traffic between pods
2. **TLS**: Enabled via OpenShift route
3. **Headers**: Security headers configured in nginx
4. **Updates**: Regularly update base images
5. **Secrets**: Use proper secret management for production

## Next Steps

1. **Test the deployment**: Access the web UI and verify functionality
2. **Configure monitoring**: Set up alerts and dashboards
3. **Optimize resources**: Adjust based on actual usage
4. **Set up CI/CD**: Automate builds on code changes
5. **Add authentication**: Implement if required for your use case
