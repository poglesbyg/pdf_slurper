# OpenShift Deployment - Data Persistence Issue Summary

## Problem Description
The submissions and samples aren't showing their full information in the OpenShift deployment. Data is not persisting between pod restarts.

## Root Causes Identified

### 1. **No Persistent Storage**
- The deployment lacks a PersistentVolumeClaim (PVC)
- Data is stored in ephemeral pod storage at `/tmp/data/`
- All data is lost when pods restart

### 2. **Database Table Mismatch**
- The application uses two sets of tables:
  - Legacy tables: `submission`, `sample` (used by upload/creation)
  - V2 tables: `submission_v2`, `sample_v2` (used by listing/retrieval)
- Data is created in legacy tables but queried from v2 tables
- This causes data to appear missing even when it exists

### 3. **Permission Errors**
- The application tries to access `/.pdf_slurper` directory at root level
- This causes "Permission denied" errors when accessing samples

### 4. **Quota Limitations**
- Cannot create PVC due to namespace quota (7Gi of 7Gi used)
- One PVC is stuck in "Terminating" status: `pvc-2bp79`

## Current Status
- ✅ API is running and functional
- ✅ Can upload PDFs and create submissions
- ⚠️ Data is not persistent across pod restarts
- ⚠️ Submissions list shows cached/old data
- ❌ Cannot retrieve samples due to permission errors
- ❌ Cannot create PVC due to quota limits

## Immediate Workaround
```bash
# Set environment variable to use correct database location
oc set env deployment/pdf-slurper-api PDF_SLURPER_DB=/tmp/data/pdf_slurper.db

# Create directory for pdf_slurper in pod
API_POD=$(oc get pod -l app=pdf-slurper,component=api -o jsonpath='{.items[0].metadata.name}')
oc exec $API_POD -- mkdir -p /tmp/.pdf_slurper
oc exec $API_POD -- chmod 777 /tmp/.pdf_slurper
```

## Permanent Solution Required

### 1. **Free Up Quota Space**
```bash
# Force delete stuck PVC
oc delete pvc pvc-2bp79 --force --grace-period=0

# Or free up space from other PVCs if possible
```

### 2. **Create PVC for Persistent Storage**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pdf-slurper-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi  # Small size due to quota
```

### 3. **Update Deployment to Use PVC**
```yaml
# Add to deployment spec
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: pdf-slurper-data
      
# Add to container spec
volumeMounts:
  - name: data
    mountPath: /tmp/data
```

### 4. **Fix Code Issues**
- Update API to use consistent table names (either legacy or v2, not both)
- Fix permission issue by using `/tmp/.pdf_slurper` instead of `/.pdf_slurper`
- Ensure both read and write operations use the same database tables

## Testing
Once fixed, test with:
```bash
# Upload a PDF
curl -X POST \
  -F "pdf_file=@test.pdf" \
  -F "storage_location=Building A" \
  https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/

# List submissions
curl https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/

# Get samples
curl https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/{id}/samples

# Restart pod and verify data persists
oc delete pod -l app=pdf-slurper,component=api
# Wait for new pod
# Test API again - data should still be there
```

## Contact for Quota Increase
If quota cannot be freed, request increase from OpenShift administrators to add at least 1Gi for pdf-slurper-data PVC.
