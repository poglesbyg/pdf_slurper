# OpenShift Deployment Fix Summary

## Issues Identified and Fixed

### 1. ✅ IndentationError in API Code
**Problem:** The API server was failing to start due to an IndentationError in `/src/presentation/api/v1/routers/submissions.py` at line 325.

**Root Cause:**
- Missing imports for database models (`LegacySubmission`, `LegacySample`, `open_session`)
- Broken SQLAlchemy query statement that was orphaned from its context
- Incorrect model names being used

**Fix Applied:**
- Added proper imports: `from pdf_slurper.db import Submission as LegacySubmission, Sample as LegacySample, open_session`
- Fixed the broken query by properly structuring it within a database session context
- Corrected the database query implementation for fetching samples

### 2. ✅ Missing Static Files (favicon.ico, index.html)
**Problem:** 404 errors for favicon.ico and index page when accessing the application.

**Root Cause:**
- The deployment was only running the API server (deployment-v2.yaml)
- API server doesn't serve static files or HTML pages
- No Web UI component was deployed

**Fix Applied:**
- Switch to using the combined deployment (deployment-combined.yaml)
- This includes both API and Web UI components
- Web UI serves static files via nginx

### 3. ✅ Deployment Configuration Issues
**Problem:** Single deployment file was insufficient for the full application.

**Solution:**
- Created `scripts/deploy-fixed.sh` that properly deploys both components
- Uses combined deployment configuration
- Ensures proper routing between Web UI and API

## Deployment Architecture

The fixed deployment uses a two-component architecture:

```
┌──────────────────────────────────────┐
│         OpenShift Route               │
│   pdf-slurper.apps.cloudapps.unc.edu │
└────────────────┬─────────────────────┘
                 │
                 ├─────────────────┐
                 ▼                 ▼
    ┌────────────────────┐  ┌────────────────────┐
    │   Web UI Service    │  │    API Service     │
    │    (Port 8080)      │  │    (Port 8080)     │
    └────────────────────┘  └────────────────────┘
              │                        │
    ┌────────────────────┐  ┌────────────────────┐
    │  Web UI Deployment  │  │   API Deployment   │
    │  - nginx            │  │  - FastAPI         │
    │  - Static HTML      │  │  - PDF Processing  │
    │  - Dashboard        │  │  - CRUD Operations │
    └────────────────────┘  └────────────────────┘
```

## Quick Deployment Steps

### 1. Login to OpenShift
```bash
oc login <your-openshift-server>
```

### 2. Run the Fixed Deployment Script
```bash
cd scripts
./deploy-fixed.sh dept-barc
```

### 3. Verify Deployment
The script will automatically:
- Build both API and Web UI images
- Deploy both components
- Set up proper routing
- Run health checks
- Display access URLs

## Testing the Fix

### Test API Health
```bash
# Get the route URL
ROUTE_URL=$(oc get route pdf-slurper -o jsonpath='{.spec.host}')

# Test API health endpoint
curl https://$ROUTE_URL/api/health

# Expected response:
# {"status":"healthy","version":"2.0.0"}
```

### Test Web UI
```bash
# Test main dashboard
curl -I https://$ROUTE_URL/

# Expected: HTTP/1.1 200 OK

# Test specific pages
curl -I https://$ROUTE_URL/dashboard.html
curl -I https://$ROUTE_URL/upload.html
```

### Test API Functionality
```bash
# List submissions
curl https://$ROUTE_URL/api/v1/submissions/

# Upload a PDF (requires actual file)
curl -X POST https://$ROUTE_URL/api/v1/submissions/upload \
  -F "file=@test.pdf" \
  -F "storage_location=Freezer-A"
```

## Monitoring

### View Logs
```bash
# API logs
oc logs -f deployment/pdf-slurper-v2

# Web UI logs  
oc logs -f deployment/pdf-slurper-web

# All pods
oc logs -l app=pdf-slurper --tail=100
```

### Check Pod Status
```bash
oc get pods -l app=pdf-slurper
```

### Check Events
```bash
oc get events --sort-by='.lastTimestamp' | grep pdf-slurper
```

## Rollback Procedure

If issues occur after deployment:

```bash
# Rollback API
oc rollout undo deployment/pdf-slurper-v2

# Rollback Web UI
oc rollout undo deployment/pdf-slurper-web

# Check rollout history
oc rollout history deployment/pdf-slurper-v2
oc rollout history deployment/pdf-slurper-web
```

## Configuration Details

### Environment Variables
The deployment uses ConfigMaps and Secrets for configuration:

**ConfigMap (pdf-slurper-config):**
- `PDF_SLURPER_ENV`: production
- `PDF_SLURPER_USE_NEW`: true
- `PDF_SLURPER_HOST`: 0.0.0.0
- `PDF_SLURPER_PORT`: 8080
- `LOG_LEVEL`: INFO
- `API_DOCS_ENABLED`: true

**Secret (pdf-slurper-secret):**
- `DATABASE_URL`: SQLite database path
- `API_KEY`: API authentication key
- `JWT_SECRET`: JWT signing secret

### Resource Limits
- API: 64Mi-128Mi memory, 60m-200m CPU
- Web UI: 64Mi-128Mi memory, 60m-100m CPU

## Security Considerations

1. **Update Secrets**: Replace default values in the Secret with secure ones:
```bash
API_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)
oc create secret generic pdf-slurper-secret \
  --from-literal=API_KEY="$API_KEY" \
  --from-literal=JWT_SECRET="$JWT_SECRET" \
  --dry-run=client -o yaml | oc apply -f -
```

2. **Network Policies**: The combined deployment includes network policies to restrict traffic.

3. **TLS**: Routes are configured with edge TLS termination.

## Next Steps

1. **Production Database**: Consider migrating from SQLite to PostgreSQL for production
2. **Monitoring**: Set up proper monitoring and alerting
3. **Backup Strategy**: Implement automated backups for the database
4. **Scaling**: Configure HPA for automatic scaling based on load
5. **CI/CD**: Set up automated build and deployment pipelines

## Support

For issues or questions:
1. Check the troubleshooting section in this document
2. Review logs as described above
3. Check OPENSHIFT_TROUBLESHOOTING.md for common issues
4. Contact the platform team for infrastructure issues

---

**Fixed By:** Development Team  
**Date:** $(date)  
**Version:** 2.0.0-fixed
