# PDF Slurper Architecture

## Overview
This document describes the modular architecture of the PDF Slurper application, following Domain-Driven Design (DDD) and Clean Architecture principles.

## Directory Structure

```
pdf_slurper/
├── src/                          # Source code
│   ├── domain/                   # Domain layer (business entities & logic)
│   │   ├── models/              # Domain models
│   │   │   ├── __init__.py
│   │   │   ├── submission.py   # Submission entity
│   │   │   ├── sample.py       # Sample entity
│   │   │   └── value_objects.py # Value objects (QCStatus, etc.)
│   │   ├── services/            # Domain services
│   │   │   ├── __init__.py
│   │   │   ├── qc_service.py   # Quality control logic
│   │   │   └── sample_tracking.py # Sample workflow logic
│   │   └── repositories/        # Repository interfaces
│   │       ├── __init__.py
│   │       ├── submission_repository.py
│   │       └── sample_repository.py
│   │
│   ├── application/             # Application layer (use cases)
│   │   ├── services/           # Application services
│   │   │   ├── __init__.py
│   │   │   ├── pdf_processor.py # PDF processing service
│   │   │   ├── submission_service.py
│   │   │   └── sample_service.py
│   │   ├── dto/                # Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   └── requests.py
│   │   └── exceptions.py       # Application exceptions
│   │
│   ├── infrastructure/          # Infrastructure layer
│   │   ├── persistence/        # Data persistence
│   │   │   ├── __init__.py
│   │   │   ├── database.py    # Database connection
│   │   │   ├── models.py      # ORM models (SQLModel)
│   │   │   ├── repositories/  # Repository implementations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── submission_repository.py
│   │   │   │   └── sample_repository.py
│   │   │   └── migrations/    # Alembic migrations
│   │   ├── pdf/               # PDF processing
│   │   │   ├── __init__.py
│   │   │   ├── extractors/    # PDF extraction strategies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── pymupdf_extractor.py
│   │   │   │   └── pdfplumber_extractor.py
│   │   │   └── parsers/       # Content parsers
│   │   │       ├── __init__.py
│   │   │       ├── metadata_parser.py
│   │   │       └── table_parser.py
│   │   └── config/            # Configuration
│   │       ├── __init__.py
│   │       ├── settings.py   # Settings management
│   │       └── logging.py    # Logging configuration
│   │
│   ├── presentation/           # Presentation layer
│   │   ├── api/              # REST API
│   │   │   ├── __init__.py
│   │   │   ├── v1/          # API v1
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── submissions.py
│   │   │   │   │   ├── samples.py
│   │   │   │   │   └── health.py
│   │   │   │   ├── schemas/  # API schemas (Pydantic)
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── submission.py
│   │   │   │   │   └── sample.py
│   │   │   │   └── dependencies.py
│   │   │   └── middleware.py
│   │   ├── cli/             # CLI interface
│   │   │   ├── __init__.py
│   │   │   ├── app.py       # Main CLI app
│   │   │   └── commands/    # CLI commands
│   │   │       ├── __init__.py
│   │   │       ├── submission.py
│   │   │       ├── sample.py
│   │   │       └── database.py
│   │   └── web/             # Web UI
│   │       ├── __init__.py
│   │       ├── app.py
│   │       └── templates/
│   │
│   └── shared/                # Shared utilities
│       ├── __init__.py
│       ├── utils.py
│       └── constants.py
│
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/          # Integration tests
│   │   ├── api/
│   │   └── persistence/
│   ├── fixtures/            # Test fixtures
│   └── conftest.py         # Pytest configuration
│
├── scripts/                  # Utility scripts
├── docs/                    # Documentation
├── .env.example            # Environment variables example
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container definition
└── docker-compose.yml      # Local development

```

## Design Principles

### 1. Separation of Concerns
- **Domain Layer**: Business logic and entities
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: External dependencies (DB, PDF libs)
- **Presentation Layer**: User interfaces (API, CLI, Web)

### 2. Dependency Inversion
- Domain and Application layers don't depend on Infrastructure
- Repository interfaces defined in Domain, implemented in Infrastructure
- Dependency injection for loose coupling

### 3. Single Responsibility
- Each module has one reason to change
- Services focused on specific business capabilities
- Clear boundaries between layers

### 4. Interface Segregation
- Small, focused interfaces
- Clients depend only on methods they use
- Repository pattern for data access abstraction

## Key Components

### Domain Models
```python
# Pure business entities without ORM dependencies
class Submission:
    id: SubmissionId
    samples: List[Sample]
    metadata: SubmissionMetadata
    
class Sample:
    id: SampleId
    measurements: Measurements
    qc_status: QCStatus
    workflow_status: WorkflowStatus
```

### Repository Pattern
```python
# Interface in domain layer
class SubmissionRepository(Protocol):
    async def get(self, id: SubmissionId) -> Optional[Submission]
    async def save(self, submission: Submission) -> None
    
# Implementation in infrastructure layer
class SQLSubmissionRepository:
    def __init__(self, session: Session):
        self.session = session
```

### Service Layer
```python
class SubmissionService:
    def __init__(
        self,
        repo: SubmissionRepository,
        pdf_processor: PDFProcessor,
        qc_service: QCService
    ):
        self.repo = repo
        self.pdf_processor = pdf_processor
        self.qc_service = qc_service
```

### Configuration Management
```python
# Pydantic settings for type-safe configuration
class Settings(BaseSettings):
    database_url: str
    pdf_max_size: int = 100_000_000
    qc_min_concentration: float = 10.0
    
    class Config:
        env_file = ".env"
```

## Testing Strategy

### Unit Tests
- Test domain logic in isolation
- Mock external dependencies
- Fast and deterministic

### Integration Tests
- Test database operations
- Test PDF processing
- Test API endpoints

### Contract Tests
- Verify repository implementations
- Ensure interface compliance

## API Design

### RESTful Endpoints
```
GET    /api/v1/submissions
POST   /api/v1/submissions
GET    /api/v1/submissions/{id}
PATCH  /api/v1/submissions/{id}
DELETE /api/v1/submissions/{id}

GET    /api/v1/submissions/{id}/samples
PATCH  /api/v1/submissions/{id}/samples/batch
POST   /api/v1/submissions/{id}/qc

GET    /api/v1/samples/{id}
PATCH  /api/v1/samples/{id}
```

### OpenAPI Documentation
- Auto-generated from FastAPI
- Available at `/docs` and `/redoc`
- Includes request/response schemas

## Error Handling

### Domain Exceptions
```python
class DomainException(Exception): pass
class InvalidSampleException(DomainException): pass
class QCThresholdException(DomainException): pass
```

### Application Exceptions
```python
class ApplicationException(Exception): pass
class SubmissionNotFoundException(ApplicationException): pass
```

### API Error Responses
```json
{
    "error": {
        "code": "SUBMISSION_NOT_FOUND",
        "message": "Submission with ID 'sub_123' not found",
        "details": {}
    }
}
```

## Logging

### Structured Logging
```python
logger.info(
    "Sample QC applied",
    extra={
        "submission_id": submission_id,
        "samples_flagged": count,
        "thresholds": {...}
    }
)
```

### Log Levels
- ERROR: Application errors
- WARNING: QC failures, validation issues
- INFO: Business events
- DEBUG: Detailed processing info

## Deployment

### Container Strategy
- Multi-stage Dockerfile
- Non-root user
- Health checks
- Graceful shutdown

### Configuration
- Environment variables for secrets
- ConfigMaps for settings
- Volume mounts for data

## Migration Path

1. **Phase 1**: Create new structure alongside existing
2. **Phase 2**: Move domain logic to domain layer
3. **Phase 3**: Implement repository pattern
4. **Phase 4**: Refactor services
5. **Phase 5**: Update presentation layer
6. **Phase 6**: Add comprehensive tests
7. **Phase 7**: Remove old code

## Benefits

1. **Maintainability**: Clear separation of concerns
2. **Testability**: Easy to test in isolation
3. **Flexibility**: Easy to swap implementations
4. **Scalability**: Can split into microservices
5. **Documentation**: Self-documenting structure
6. **Team Collaboration**: Clear boundaries
