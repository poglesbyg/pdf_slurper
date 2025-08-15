# Production Deployment Guide

## 🚀 PDF Slurper v2 - Production Migration

This guide covers the complete production deployment process for migrating from the monolithic architecture to the new modular architecture.

## 📋 Pre-Deployment Checklist

### 1. System Requirements
- [ ] Python 3.11+
- [ ] Docker 20.10+
- [ ] OpenShift CLI (oc) 4.10+
- [ ] 10GB storage for data persistence
- [ ] PostgreSQL 15+ (for production)

### 2. Migration Readiness
```bash
# Check migration status
uv run python pdf_slurper/cli_v2.py migrate-check

# Run parallel tests
uv run python scripts/parallel_test.py

# Verify test coverage
./run_tests.sh
```

## 🔄 Migration Process

### Phase 1: Parallel Testing (Week 1)

#### 1.1 Run Both Systems Side-by-Side
```bash
# Start new API (port 8080)
PDF_SLURPER_USE_NEW=true python run_api.py &

# Start legacy system (port 8000)
PDF_SLURPER_USE_NEW=false uv run pdf-slurp-web &

# Compare results
uv run python scripts/parallel_test.py HTSF--JL-147_quote_160217072025.pdf
```

#### 1.2 Validate Results
- ✅ Same number of samples extracted
- ✅ Identical submission metadata
- ✅ Performance metrics acceptable
- ✅ No data loss or corruption

### Phase 2: Deploy to Staging (Week 2)

#### 2.1 Build Docker Image
```bash
# Build v2 image
docker build -f Dockerfile.v2 -t pdf-slurper:v2 \
  --build-arg VERSION=2.0.0 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) .

# Test locally
docker run -p 8080:8080 -p 3000:3000 pdf-slurper:v2
```

#### 2.2 Deploy to OpenShift Staging
```bash
# Login to OpenShift
oc login <cluster-url>

# Deploy to staging
./scripts/deploy.sh pdf-slurper-staging staging v2

# Verify deployment
oc get pods -l app=pdf-slurper,version=v2
oc logs -f deployment/pdf-slurper-v2
```

#### 2.3 Run Integration Tests
```bash
# Health checks
curl https://pdf-slurper-staging.apps.cloudapps.unc.edu/health
curl https://pdf-slurper-staging.apps.cloudapps.unc.edu/ready

# API tests
curl https://pdf-slurper-staging.apps.cloudapps.unc.edu/api/docs
```

### Phase 3: Production Deployment (Week 3)

#### 3.1 Database Migration
```bash
# Backup existing database
oc exec deployment/pdf-slurper -- tar czf /tmp/backup.tar.gz /data
oc cp pdf-slurper-<pod>:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz

# Run Alembic migrations
uv run alembic upgrade head
```

#### 3.2 Blue-Green Deployment
```bash
# Deploy v2 alongside v1
./scripts/deploy.sh pdf-slurper-prod production v2

# Gradually shift traffic (canary deployment)
oc set route-backends pdf-slurper \
  pdf-slurper-v1=50 \
  pdf-slurper-v2=50

# Monitor metrics
oc logs -f deployment/pdf-slurper-v2 | grep ERROR

# Full cutover
oc set route-backends pdf-slurper \
  pdf-slurper-v1=0 \
  pdf-slurper-v2=100
```

#### 3.3 Monitoring Setup
```bash
# Check metrics endpoint
curl https://pdf-slurper.apps.cloudapps.unc.edu/metrics

# View HPA status
oc get hpa pdf-slurper-v2-hpa

# Check resource usage
oc top pods -l app=pdf-slurper,version=v2
```

### Phase 4: Cleanup (Week 4)

#### 4.1 Validate New System
```bash
# Run smoke tests
uv run python scripts/parallel_test.py --production

# Check logs for errors
oc logs deployment/pdf-slurper-v2 --since=24h | grep -E "ERROR|CRITICAL"

# Verify data integrity
uv run python pdf_slurper/cli_v2.py stats <submission-id>
```

#### 4.2 Remove Legacy Code
```bash
# Preview cleanup
uv run python scripts/cleanup_legacy.py preview

# Check migration status
uv run python scripts/cleanup_legacy.py check

# Execute cleanup (creates archive)
uv run python scripts/cleanup_legacy.py execute

# List archives (for rollback if needed)
uv run python scripts/cleanup_legacy.py list-archives
```

#### 4.3 Scale Down Legacy
```bash
# Stop legacy deployment
oc scale deployment/pdf-slurper-v1 --replicas=0

# After validation period, delete legacy resources
oc delete deployment pdf-slurper-v1
oc delete service pdf-slurper-v1
oc delete route pdf-slurper-v1
```

## 🔧 Configuration

### Environment Variables

#### Production Settings
```bash
PDF_SLURPER_ENV=production
PDF_SLURPER_USE_NEW=true
PDF_SLURPER_HOST=0.0.0.0
PDF_SLURPER_PORT=8080
DATABASE_URL=postgresql://user:pass@db:5432/pdfslurper
LOG_LEVEL=WARNING
API_DOCS_ENABLED=false
WORKERS=4
QC_AUTO_APPLY=true
QC_MIN_CONCENTRATION=10.0
QC_MIN_VOLUME=20.0
QC_MIN_RATIO=1.8
```

### Docker Compose (Local Testing)
```bash
# Start all services
docker-compose up -d

# Start with PostgreSQL
docker-compose --profile postgres up -d

# Start with monitoring
docker-compose --profile cache --profile proxy up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

## 📊 Monitoring & Alerts

### Key Metrics to Monitor
1. **Application Health**
   - Health endpoint status
   - Ready endpoint status
   - Pod restart count

2. **Performance**
   - API response time (p50, p95, p99)
   - PDF processing time
   - Database query time

3. **Resources**
   - CPU usage < 70%
   - Memory usage < 80%
   - Disk usage < 90%

4. **Business Metrics**
   - Submissions processed/hour
   - Samples created/day
   - QC pass rate

### Alert Thresholds
```yaml
alerts:
  - name: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    severity: warning
    
  - name: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    severity: critical
    
  - name: HighMemoryUsage
    expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
    severity: warning
```

## 🔄 Rollback Plan

### Quick Rollback (< 5 minutes)
```bash
# Rollback deployment
oc rollout undo deployment/pdf-slurper-v2

# Or switch traffic back to v1
oc set route-backends pdf-slurper \
  pdf-slurper-v1=100 \
  pdf-slurper-v2=0
```

### Full Rollback (< 30 minutes)
```bash
# Restore from archive
uv run python scripts/cleanup_legacy.py restore 20240101_120000

# Restore database backup
oc cp backup-20240101.tar.gz pdf-slurper-<pod>:/tmp/
oc exec deployment/pdf-slurper -- tar xzf /tmp/backup.tar.gz -C /

# Redeploy v1
oc rollout restart deployment/pdf-slurper-v1
```

## 🎯 Success Criteria

### Go/No-Go Decision Points

#### Staging (Week 2)
- [ ] All integration tests pass
- [ ] Performance meets SLA (< 2s response time)
- [ ] No critical bugs found
- [ ] Team trained on new system

#### Production (Week 3)
- [ ] Canary deployment successful (24 hours)
- [ ] Error rate < 0.1%
- [ ] No data loss incidents
- [ ] Rollback tested successfully

#### Final (Week 4)
- [ ] 7 days stable in production
- [ ] All monitoring configured
- [ ] Documentation updated
- [ ] Legacy code archived

## 📚 Documentation

### API Documentation
- Development: http://localhost:8080/api/docs
- Staging: https://pdf-slurper-staging.apps.cloudapps.unc.edu/api/docs
- Production: Internal only (disabled for security)

### Architecture Documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Migration strategy
- [MIGRATION_STATUS.md](./MIGRATION_STATUS.md) - Current status

### Runbooks
1. **Incident Response**: See `docs/runbooks/incident-response.md`
2. **Database Maintenance**: See `docs/runbooks/database-maintenance.md`
3. **Performance Tuning**: See `docs/runbooks/performance-tuning.md`

## 🤝 Support

### Escalation Path
1. **L1 Support**: Check health endpoints and logs
2. **L2 Support**: Restart pods, check database
3. **L3 Support**: Development team, architecture review

### Contact Information
- **On-Call**: See PagerDuty rotation
- **Slack Channel**: #pdf-slurper-support
- **Email**: pdf-slurper-team@example.com

## 🎉 Post-Deployment

### Week 5-6: Optimization
- [ ] Performance profiling
- [ ] Database query optimization
- [ ] Caching implementation
- [ ] Load testing

### Week 7-8: Enhancement
- [ ] Add new features
- [ ] Improve UI/UX
- [ ] Expand API capabilities
- [ ] Machine learning integration

---

## Quick Commands Reference

```bash
# Check system status
uv run python pdf_slurper/cli_v2.py migrate-check

# Run parallel tests
uv run python scripts/parallel_test.py

# Deploy to staging
./scripts/deploy.sh pdf-slurper-staging staging v2

# Deploy to production
./scripts/deploy.sh pdf-slurper-prod production v2

# Check deployment status
./scripts/deploy.sh pdf-slurper-prod production v2 status

# Rollback if needed
./scripts/deploy.sh pdf-slurper-prod production v2 rollback

# Cleanup legacy code
uv run python scripts/cleanup_legacy.py execute

# Start new API locally
PDF_SLURPER_USE_NEW=true python run_api.py

# Run tests
./run_tests.sh
```

---

**Last Updated**: $(date)
**Version**: 2.0.0
**Status**: Ready for Production Deployment
