# Migration Guide: Monolith to Modular Architecture

## Overview
This guide provides step-by-step instructions for migrating from the current monolithic codebase to the new modular architecture.

## Benefits of Migration

### Current Issues
- **Tight Coupling**: Business logic mixed with infrastructure
- **Hard to Test**: Difficult to unit test without database
- **Limited Flexibility**: Hard to swap implementations
- **Code Duplication**: Similar logic repeated across files
- **Unclear Boundaries**: No clear separation of concerns

### New Architecture Benefits
- **Clean Separation**: Domain, Application, Infrastructure, Presentation layers
- **Testable**: Easy unit testing with dependency injection
- **Flexible**: Repository pattern allows swapping data stores
- **DRY**: Shared business logic in domain services
- **Clear Boundaries**: Each layer has specific responsibilities

## Migration Phases

### Phase 1: Setup New Structure (Week 1)
**Goal**: Create new directory structure alongside existing code

```bash
# Create new structure
mkdir -p src/{domain,application,infrastructure,presentation}
mkdir -p tests/{unit,integration,fixtures}

# Copy architecture files
cp ARCHITECTURE.md src/
```

**Tasks**:
- [x] Create directory structure
- [x] Setup domain models and value objects
- [x] Define repository interfaces
- [x] Create configuration management
- [ ] Setup logging infrastructure
- [ ] Create base test fixtures

### Phase 2: Domain Layer (Week 2)
**Goal**: Extract business logic to domain layer

**Current Code → Domain Mapping**:
```python
# Old: pdf_slurper/db.py
class Sample(SQLModel):
    # ORM model with business logic mixed

# New: src/domain/models/sample.py
class Sample:
    # Pure domain entity
    
# New: src/infrastructure/persistence/models.py
class SampleORM(SQLModel):
    # ORM model only
```

**Tasks**:
- [ ] Extract Sample business logic to domain
- [ ] Extract Submission business logic to domain
- [ ] Create value objects for IDs, measurements
- [ ] Define domain services (QC, workflow)
- [ ] Write domain unit tests

### Phase 3: Repository Implementation (Week 3)
**Goal**: Implement repository pattern

**Migration Steps**:
1. Create repository implementations in infrastructure
2. Map between domain models and ORM models
3. Move database queries to repositories

```python
# Old way
def list_submissions(session, limit=50):
    stmt = select(Submission).limit(limit)
    return session.exec(stmt)

# New way
class SQLSubmissionRepository:
    async def get_all(self, pagination):
        # Implementation with proper mapping
```

**Tasks**:
- [ ] Implement SQLSubmissionRepository
- [ ] Implement SQLSampleRepository
- [ ] Create model mappers (domain ↔ ORM)
- [ ] Write repository integration tests
- [ ] Add caching layer (optional)

### Phase 4: Application Services (Week 4)
**Goal**: Create service layer for orchestration

**Migration Mapping**:
- `slurp.py` → `PDFProcessor` + `SubmissionService`
- `cli.py` commands → Application services
- `server.py` endpoints → Service calls

**Tasks**:
- [ ] Create SubmissionService
- [ ] Create SampleService
- [ ] Implement PDFProcessor with strategies
- [ ] Add transaction management
- [ ] Write service unit tests

### Phase 5: API Migration (Week 5)
**Goal**: Migrate REST API to new structure

**Changes**:
1. Use FastAPI routers for organization
2. Add API versioning (/api/v1)
3. Use Pydantic schemas for validation
4. Implement proper error handling

```python
# Old: server.py
@app.get("/submission/{id}")
def view_submission(id: str):
    # Direct database access

# New: src/presentation/api/v1/routers/submissions.py
@router.get("/{id}", response_model=SubmissionResponse)
async def get_submission(
    id: str,
    service: SubmissionService = Depends(get_submission_service)
):
    # Use service layer
```

**Tasks**:
- [ ] Create API routers
- [ ] Define request/response schemas
- [ ] Add OpenAPI documentation
- [ ] Implement middleware (auth, logging)
- [ ] Write API integration tests

### Phase 6: CLI Migration (Week 6)
**Goal**: Refactor CLI to use services

**Changes**:
- Split commands into modules
- Use dependency injection
- Add proper error handling
- Improve output formatting

**Tasks**:
- [ ] Refactor submission commands
- [ ] Refactor sample commands
- [ ] Refactor database commands
- [ ] Add progress indicators
- [ ] Write CLI tests

### Phase 7: Testing & Documentation (Week 7)
**Goal**: Comprehensive testing and documentation

**Testing Strategy**:
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Database, API tests
├── e2e/           # End-to-end workflows
└── performance/   # Load testing
```

**Tasks**:
- [ ] Write unit tests (80% coverage target)
- [ ] Write integration tests
- [ ] Create test data factories
- [ ] Update API documentation
- [ ] Write developer guide

### Phase 8: Deployment Updates (Week 8)
**Goal**: Update deployment for new architecture

**Changes**:
- Multi-stage Docker build
- Environment-based configuration
- Health checks with dependencies
- Graceful shutdown
- Database migrations with Alembic

**Tasks**:
- [ ] Update Dockerfile
- [ ] Create docker-compose for development
- [ ] Update OpenShift manifests
- [ ] Setup CI/CD pipeline
- [ ] Create deployment runbook

## Code Migration Examples

### Example 1: Migrating Sample QC Logic

**Before** (pdf_slurper/db.py):
```python
def apply_qc_thresholds(session, submission_id, min_concentration=10.0):
    samples = list_samples_for_submission(session, submission_id)
    for sample in samples:
        if sample.qubit_ng_per_ul < min_concentration:
            sample.qc_status = "failed"
    session.commit()
```

**After** (domain + service):
```python
# Domain layer
class Sample:
    def apply_qc(self, thresholds: QCThresholds) -> QCResult:
        # Pure business logic, no database
        
# Application layer
class SampleService:
    async def apply_qc_batch(self, submission_id, thresholds):
        submission = await self.repository.get(submission_id)
        results = submission.apply_qc_to_all(thresholds)
        await self.repository.save(submission)
        return results
```

### Example 2: Migrating PDF Processing

**Before** (pdf_slurper/slurp.py):
```python
def slurp_pdf(pdf_path, db_path=None):
    # Everything in one function
    with fitz.open(pdf_path) as doc:
        # Extract metadata
    with pdfplumber.open(pdf_path) as pdf:
        # Extract tables
    with open_session(db_path) as session:
        # Save to database
```

**After** (modular):
```python
# Infrastructure layer
class PyMuPDFExtractor:
    async def extract_metadata(self, pdf_path):
        # Metadata extraction only

class PDFPlumberExtractor:
    async def extract_tables(self, pdf_path):
        # Table extraction only

# Application layer
class PDFProcessor:
    async def process(self, pdf_path):
        metadata = await self.metadata_extractor.extract(pdf_path)
        tables = await self.table_extractor.extract(pdf_path)
        return ProcessingResult(metadata, tables)
```

## Testing During Migration

### Test Strategy
1. **Keep existing tests running** during migration
2. **Write tests for new code** before migrating
3. **Use adapters** to bridge old and new code
4. **Run parallel systems** for validation

### Example Test
```python
# Test both old and new implementations
def test_qc_compatibility():
    # Old way
    old_result = old_apply_qc(sample_data)
    
    # New way
    new_result = new_service.apply_qc(sample_data)
    
    # Verify same results
    assert old_result == new_result
```

## Rollback Plan

If issues arise during migration:

1. **Feature flags**: Toggle between old/new implementations
2. **Database compatibility**: Keep schemas compatible
3. **API versioning**: Maintain v0 endpoints during transition
4. **Gradual rollout**: Migrate one component at a time

## Success Metrics

Track these metrics to measure migration success:

- **Code coverage**: Target 80% unit test coverage
- **Performance**: No regression in API response times
- **Reliability**: Error rate < 0.1%
- **Development velocity**: Faster feature development
- **Code quality**: Reduced cyclomatic complexity

## Common Pitfalls

### Avoid These Mistakes
1. **Big Bang Migration**: Don't try to migrate everything at once
2. **Breaking Changes**: Maintain backward compatibility
3. **Skipping Tests**: Write tests before migrating
4. **Ignoring Performance**: Profile before and after
5. **Poor Communication**: Keep team informed of changes

## Support

### Resources
- Architecture documentation: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Example implementations: [src/examples/](./src/examples/)
- Test fixtures: [tests/fixtures/](./tests/fixtures/)

### Getting Help
- Create issues for blockers
- Use feature branches for experiments
- Pair program on complex migrations
- Review PRs thoroughly

## Timeline

| Week | Phase | Status |
|------|-------|--------|
| 1 | Setup Structure | ✅ Complete |
| 2 | Domain Layer | 🔄 In Progress |
| 3 | Repositories | ⏳ Pending |
| 4 | Services | ⏳ Pending |
| 5 | API Migration | ⏳ Pending |
| 6 | CLI Migration | ⏳ Pending |
| 7 | Testing | ⏳ Pending |
| 8 | Deployment | ⏳ Pending |

## Checklist

### Pre-Migration
- [ ] Backup current database
- [ ] Document current API
- [ ] Inventory dependencies
- [ ] Setup development environment
- [ ] Create migration branch

### During Migration
- [ ] Run tests continuously
- [ ] Monitor performance
- [ ] Document changes
- [ ] Update dependencies
- [ ] Review code regularly

### Post-Migration
- [ ] Remove old code
- [ ] Update documentation
- [ ] Train team
- [ ] Monitor production
- [ ] Gather feedback

## Conclusion

This migration will transform the codebase into a maintainable, testable, and scalable application. Follow the phases sequentially, test thoroughly, and maintain backward compatibility throughout the process.
