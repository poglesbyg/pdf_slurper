# OpenShift Deployment Troubleshooting Guide

## Fixed Issues

### 1. ✅ Image Reference Issues
**Problem:** Image reference `pdf-slurper:v2` was not using the full registry path.
**Solution:** Updated to use internal registry: `image-registry.openshift-image-registry.svc:5000/dept-barc/pdf-slurper:v2`

### 2. ✅ Volume Mount Path Inconsistency
**Problem:** Data volume was mounted at `/app/data` but database expected `/data`.
**Solution:** Standardized all volume mounts to `/data` for database consistency.

### 3. ✅ Security Context Conflicts
**Problem:** Hardcoded UID/GID values conflicted with OpenShift Security Context Constraints.
**Solution:** Removed security context to let OpenShift apply its defaults.

### 4. ✅ Invalid Secret Generation
**Problem:** Shell command syntax `$(openssl rand -hex 32)` in secret stringData.
**Solution:** Replaced with static secure values or use the deployment script to generate.

### 5. ✅ Resource Limits
**Problem:** Memory limits too low (256Mi) for PDF processing.
**Solution:** Increased to 1Gi limit with 256Mi request.

## Deployment Steps

### Quick Deploy
```bash
# Using the deployment script
cd scripts
./deploy-openshift.sh dept-barc

# Or manually
oc apply -f openshift/deployment-v2.yaml
```

### Build and Deploy from Source
```bash
# 1. Login to OpenShift
oc login <your-openshift-server>

# 2. Create/switch to your namespace
oc project dept-barc

# 3. Build the image (if needed)
oc new-build --name=pdf-slurper-v2 \
  --binary \
  --strategy=docker \
  --dockerfile=Dockerfile.v2

oc start-build pdf-slurper-v2 --from-dir=. --follow

# 4. Apply deployment
oc apply -f openshift/deployment-v2.yaml

# 5. Check deployment status
oc rollout status deployment/pdf-slurper-v2
```

## Common Issues and Solutions

### Pod Fails to Start

1. **Check logs:**
```bash
oc logs -f deployment/pdf-slurper-v2
```

2. **Check events:**
```bash
oc get events --sort-by='.lastTimestamp'
```

3. **Describe pod:**
```bash
oc describe pod -l app=pdf-slurper,version=v2
```

### Permission Denied Errors

If you see permission errors:
```bash
# Check SCC (Security Context Constraints)
oc get pod -l app=pdf-slurper -o yaml | grep scc

# If needed, add anyuid SCC (not recommended for production)
oc adm policy add-scc-to-user anyuid -z default
```

### Image Pull Errors

```bash
# Check if image exists
oc get is pdf-slurper

# Check image registry accessibility
oc get is pdf-slurper -o yaml

# Manually import image if needed
oc import-image pdf-slurper:v2 --from=<your-registry>/pdf-slurper:v2 --confirm
```

### Database Connection Issues

```bash
# Check if PVC is bound
oc get pvc pdf-slurper-data-v2

# Check volume mounts in pod
oc exec deployment/pdf-slurper-v2 -- ls -la /data

# Check database file permissions
oc exec deployment/pdf-slurper-v2 -- ls -la /data/pdf_slurper.db
```

### Health Check Failures

```bash
# Test health endpoint directly
oc exec deployment/pdf-slurper-v2 -- curl localhost:8080/health

# Check if port is listening
oc exec deployment/pdf-slurper-v2 -- netstat -tlnp | grep 8080

# Port forward for local testing
oc port-forward deployment/pdf-slurper-v2 8080:8080
curl http://localhost:8080/health
```

### Route Not Working

```bash
# Check route status
oc get route pdf-slurper-v2

# Test route directly
curl -v https://$(oc get route pdf-slurper-v2 -o jsonpath='{.spec.host}')/health

# Check if service endpoints exist
oc get endpoints pdf-slurper-v2
```

## Monitoring

### View Logs
```bash
# Application logs
oc logs -f deployment/pdf-slurper-v2

# Previous pod logs (if crashed)
oc logs deployment/pdf-slurper-v2 --previous

# All pods logs
oc logs -l app=pdf-slurper --tail=100
```

### Resource Usage
```bash
# Check resource usage
oc adm top pod -l app=pdf-slurper

# Check HPA status
oc get hpa pdf-slurper-v2-hpa
```

### Debugging Inside Pod
```bash
# Execute shell in pod
oc exec -it deployment/pdf-slurper-v2 -- /bin/bash

# Run commands inside pod
oc exec deployment/pdf-slurper-v2 -- python -c "from src.infrastructure.config.settings import get_settings; print(get_settings())"
```

## Rollback

If deployment fails:
```bash
# Check rollout history
oc rollout history deployment/pdf-slurper-v2

# Rollback to previous version
oc rollout undo deployment/pdf-slurper-v2

# Rollback to specific revision
oc rollout undo deployment/pdf-slurper-v2 --to-revision=2
```

## Production Checklist

- [ ] Generate secure API_KEY and JWT_SECRET
- [ ] Configure proper database (PostgreSQL recommended)
- [ ] Set up proper storage class for PVC
- [ ] Configure backup strategy for data volume
- [ ] Set up monitoring and alerting
- [ ] Configure network policies if required
- [ ] Review and adjust resource limits based on load
- [ ] Enable TLS for route
- [ ] Configure proper logging aggregation

## Support

For additional help:
1. Check OpenShift documentation
2. Review application logs
3. Contact platform team if infrastructure issues persist
