# OpenShift Deployment TODO List

## 📋 Pre-Deployment Phase

### 1. Backup & Preparation
- [ ] **Backup existing production data**
  ```bash
  oc exec deployment/pdf-slurper -- tar czf /tmp/backup.tar.gz /data
  oc cp pdf-slurper-<pod>:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
  ```
- [ ] **Document current version and configuration**
- [ ] **Create rollback plan**

### 2. Code & Image Preparation
- [ ] **Test CRUD operations locally**
  ```bash
  # Start services
  uv run python start_services.py
  # Test API endpoints
  curl -X GET http://localhost:8080/api/v1/submissions/
  curl -X PATCH http://localhost:8080/api/v1/submissions/{id} -H "Content-Type: application/json" -d '{"storage_location": "New Location"}'
  curl -X POST http://localhost:8080/api/v1/submissions/{id}/samples -H "Content-Type: application/json" -d '{"name": "Test Sample"}'
  ```

- [ ] **Build Docker images**
  ```bash
  # Build API image with CRUD features
  docker build -f Dockerfile.v2 -t pdf-slurper:v2-crud \
    --build-arg VERSION=2.1.0-crud \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg VCS_REF=$(git rev-parse --short HEAD) .
  
  # Build Web UI image
  docker build -f Dockerfile.web -t pdf-slurper-web:v2-crud .
  ```

- [ ] **Test Docker images locally**
  ```bash
  docker-compose up -d
  docker-compose logs -f
  ```

### 3. Security Configuration
- [ ] **Generate secure secrets**
  ```bash
  API_KEY=$(openssl rand -hex 32)
  JWT_SECRET=$(openssl rand -hex 64)
  SECRET_KEY=$(openssl rand -hex 32)
  echo "API_KEY: $API_KEY"
  echo "JWT_SECRET: $JWT_SECRET"
  echo "SECRET_KEY: $SECRET_KEY"
  ```
- [ ] **Configure CORS settings for production**
- [ ] **Set up authentication/authorization (if needed)**
- [ ] **Review security best practices**
  - Input validation for CRUD operations
  - SQL injection prevention
  - XSS protection
  - Rate limiting

## 🚀 Staging Deployment

### 4. OpenShift Setup
- [ ] **Login to OpenShift**
  ```bash
  oc login <your-openshift-server>
  oc project <your-namespace>
  ```

- [ ] **Create/update ConfigMap**
  ```yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: pdf-slurper-config
  data:
    PDF_SLURPER_ENV: "staging"
    PDF_SLURPER_USE_NEW: "true"
    PDF_SLURPER_HOST: "0.0.0.0"
    PDF_SLURPER_PORT: "8080"
    WEB_UI_PORT: "3000"
    LOG_LEVEL: "INFO"
    DATABASE_URL: "sqlite:////data/pdf_slurper.db"
    ENABLE_CRUD: "true"
  ```

- [ ] **Create Secret with secure values**
  ```bash
  oc create secret generic pdf-slurper-secret \
    --from-literal=API_KEY="$API_KEY" \
    --from-literal=JWT_SECRET="$JWT_SECRET" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --dry-run=client -o yaml | oc apply -f -
  ```

### 5. Resource Configuration
- [ ] **Update PVC for data persistence**
  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: pdf-slurper-data-v2
  spec:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 10Gi  # Increased for CRUD operations
  ```

- [ ] **Configure resource limits**
  ```yaml
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "1Gi"  # Increased for handling CRUD operations
      cpu: "500m"
  ```

### 6. Deploy to Staging
- [ ] **Push images to registry**
  ```bash
  # Tag images
  docker tag pdf-slurper:v2-crud ${REGISTRY}/${NAMESPACE}/pdf-slurper:v2-crud
  docker tag pdf-slurper-web:v2-crud ${REGISTRY}/${NAMESPACE}/pdf-slurper-web:v2-crud
  
  # Push to registry
  docker push ${REGISTRY}/${NAMESPACE}/pdf-slurper:v2-crud
  docker push ${REGISTRY}/${NAMESPACE}/pdf-slurper-web:v2-crud
  ```

- [ ] **Deploy using script**
  ```bash
  cd scripts
  ./deploy-openshift.sh <staging-namespace>
  ```

- [ ] **Verify deployment**
  ```bash
  oc get pods -l app=pdf-slurper
  oc logs -f deployment/pdf-slurper-v2
  oc get route
  ```

### 7. Staging Testing
- [ ] **Test health endpoints**
  ```bash
  ROUTE_URL=$(oc get route pdf-slurper-v2 -o jsonpath='{.spec.host}')
  curl https://${ROUTE_URL}/health
  curl https://${ROUTE_URL}/api/health
  ```

- [ ] **Test CRUD operations**
  - [ ] List all submissions
  - [ ] Create new submission (upload PDF)
  - [ ] Update submission metadata
  - [ ] Add new sample to submission
  - [ ] Edit existing sample
  - [ ] Delete sample
  - [ ] Delete submission

- [ ] **Performance testing**
  ```bash
  # Load test with parallel requests
  for i in {1..10}; do
    curl -X GET https://${ROUTE_URL}/api/v1/submissions/ &
  done
  wait
  ```

## 🎯 Production Deployment

### 8. Database Migration
- [ ] **Backup production database**
- [ ] **Run Alembic migrations**
  ```bash
  oc exec -it deployment/pdf-slurper-v2 -- alembic upgrade head
  ```
- [ ] **Verify database schema**

### 9. Blue-Green Deployment
- [ ] **Deploy new version alongside existing**
  ```bash
  # Deploy green (new) version
  oc apply -f openshift/deployment-v2-green.yaml
  
  # Keep blue (current) version running
  oc get deployment pdf-slurper-v2-blue
  ```

- [ ] **Test green deployment**
  ```bash
  # Port forward to test directly
  oc port-forward deployment/pdf-slurper-v2-green 8080:8080
  ```

- [ ] **Switch traffic to green**
  ```bash
  # Update route to point to green service
  oc patch route pdf-slurper-v2 -p '{"spec":{"to":{"name":"pdf-slurper-v2-green"}}}'
  ```

- [ ] **Monitor for issues**
  ```bash
  oc logs -f deployment/pdf-slurper-v2-green
  oc get events --sort-by='.lastTimestamp'
  ```

- [ ] **Complete cutover or rollback**
  ```bash
  # If successful, remove blue deployment
  oc delete deployment pdf-slurper-v2-blue
  
  # If issues, rollback
  oc patch route pdf-slurper-v2 -p '{"spec":{"to":{"name":"pdf-slurper-v2-blue"}}}'
  ```

## 📊 Post-Deployment

### 10. Monitoring Setup
- [ ] **Configure application metrics**
- [ ] **Set up log aggregation**
  ```bash
  oc logs -f deployment/pdf-slurper-v2 --since=1h
  ```
- [ ] **Create alerts for:**
  - API response times > 2s
  - Error rates > 1%
  - Memory usage > 80%
  - Disk usage > 90%
  - Failed CRUD operations

### 11. Verification
- [ ] **Verify all endpoints**
  ```bash
  # API Documentation
  curl https://${ROUTE_URL}/api/docs
  
  # Submission CRUD
  curl -X GET https://${ROUTE_URL}/api/v1/submissions/
  curl -X PATCH https://${ROUTE_URL}/api/v1/submissions/{id}
  curl -X DELETE https://${ROUTE_URL}/api/v1/submissions/{id}
  
  # Sample CRUD
  curl -X GET https://${ROUTE_URL}/api/v1/submissions/{id}/samples
  curl -X POST https://${ROUTE_URL}/api/v1/submissions/{id}/samples
  curl -X PATCH https://${ROUTE_URL}/api/v1/submissions/{id}/samples/{sample_id}
  curl -X DELETE https://${ROUTE_URL}/api/v1/submissions/{id}/samples/{sample_id}
  ```

- [ ] **Test Web UI features**
  - [ ] Upload new PDF with storage location
  - [ ] Edit submission metadata
  - [ ] Add/edit/delete samples
  - [ ] Export data (JSON/CSV)

- [ ] **Load testing**
- [ ] **Security scanning**

### 12. Documentation
- [ ] **Update API documentation**
- [ ] **Create user guide for CRUD features**
- [ ] **Document deployment process**
- [ ] **Update runbook with:**
  - New API endpoints
  - CRUD operation procedures
  - Troubleshooting guide
  - Rollback procedures

## 🔄 Rollback Plan

If issues occur:
1. **Immediate rollback**
   ```bash
   oc rollout undo deployment/pdf-slurper-v2
   ```

2. **Check rollout history**
   ```bash
   oc rollout history deployment/pdf-slurper-v2
   ```

3. **Rollback to specific version**
   ```bash
   oc rollout undo deployment/pdf-slurper-v2 --to-revision=<previous-stable>
   ```

4. **Restore database backup if needed**
   ```bash
   oc cp ./backup-<date>.tar.gz pdf-slurper-<pod>:/tmp/
   oc exec deployment/pdf-slurper -- tar xzf /tmp/backup-<date>.tar.gz -C /
   ```

## 📌 Important Notes

1. **Database Considerations**
   - SQLite is used in current setup
   - Consider PostgreSQL for production with CRUD operations
   - Ensure proper connection pooling

2. **Security**
   - Enable HTTPS only
   - Implement rate limiting for CRUD operations
   - Add audit logging for all modifications
   - Consider adding authentication middleware

3. **Performance**
   - Monitor response times for CRUD operations
   - Implement caching where appropriate
   - Consider async processing for heavy operations

4. **High Availability**
   - Scale to multiple replicas after testing
   - Configure session affinity if needed
   - Set up database replication

## ✅ Sign-off Checklist

- [ ] All CRUD operations tested and working
- [ ] Performance acceptable (< 2s response time)
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Monitoring and alerts configured
- [ ] Rollback plan tested
- [ ] Stakeholders notified
- [ ] Go-live approval received

## 📞 Support Contacts

- Platform Team: [platform-team@example.com]
- DevOps Lead: [devops-lead@example.com]
- On-call: [PagerDuty/Slack/Teams]

---

**Last Updated:** $(date)
**Version:** 2.1.0-CRUD
**Author:** PDF Slurper Team
