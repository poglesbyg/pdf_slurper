"""Shared exception classes for the application."""

from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes."""
    # Domain errors (1xxx)
    INVALID_SAMPLE = "1001"
    INVALID_SUBMISSION = "1002"
    QC_THRESHOLD_FAILED = "1003"
    WORKFLOW_STATE_ERROR = "1004"
    
    # Application errors (2xxx)
    SUBMISSION_NOT_FOUND = "2001"
    SAMPLE_NOT_FOUND = "2002"
    DUPLICATE_SUBMISSION = "2003"
    INVALID_REQUEST = "2004"
    OPERATION_FAILED = "2005"
    
    # Infrastructure errors (3xxx)
    DATABASE_ERROR = "3001"
    FILE_NOT_FOUND = "3002"
    PDF_EXTRACTION_ERROR = "3003"
    NETWORK_ERROR = "3004"
    STORAGE_ERROR = "3005"
    
    # API errors (4xxx)
    AUTHENTICATION_FAILED = "4001"
    AUTHORIZATION_FAILED = "4002"
    RATE_LIMIT_EXCEEDED = "4003"
    INVALID_API_KEY = "4004"
    
    # System errors (5xxx)
    INTERNAL_ERROR = "5000"
    SERVICE_UNAVAILABLE = "5001"
    CONFIGURATION_ERROR = "5002"
    DEPENDENCY_ERROR = "5003"


class BaseException(Exception):
    """Base exception class with error code and context."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize exception.
        
        Args:
            message: Error message
            code: Error code
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result = {
            "code": self.code.value,
            "message": self.message,
            "details": self.details
        }
        
        if self.cause:
            result["cause"] = str(self.cause)
        
        return result
    
    def __str__(self) -> str:
        """String representation."""
        parts = [f"[{self.code.value}] {self.message}"]
        
        if self.details:
            parts.append(f"Details: {self.details}")
        
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        
        return " | ".join(parts)


# Domain Exceptions

class DomainException(BaseException):
    """Base class for domain exceptions."""
    pass


class InvalidSampleException(DomainException):
    """Invalid sample data."""
    
    def __init__(self, message: str, sample_id: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_SAMPLE,
            details={"sample_id": sample_id} if sample_id else {},
            **kwargs
        )


class InvalidSubmissionException(DomainException):
    """Invalid submission data."""
    
    def __init__(self, message: str, submission_id: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_SUBMISSION,
            details={"submission_id": submission_id} if submission_id else {},
            **kwargs
        )


class QCThresholdException(DomainException):
    """QC threshold validation failed."""
    
    def __init__(self, message: str, issues: List[str], **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.QC_THRESHOLD_FAILED,
            details={"issues": issues},
            **kwargs
        )


class WorkflowStateException(DomainException):
    """Invalid workflow state transition."""
    
    def __init__(self, message: str, current_state: str, target_state: str, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.WORKFLOW_STATE_ERROR,
            details={
                "current_state": current_state,
                "target_state": target_state
            },
            **kwargs
        )


# Application Exceptions

class ApplicationException(BaseException):
    """Base class for application exceptions."""
    pass


class EntityNotFoundException(ApplicationException):
    """Entity not found."""
    
    def __init__(self, entity_type: str, entity_id: str, **kwargs):
        super().__init__(
            message=f"{entity_type} not found: {entity_id}",
            code=ErrorCode.SUBMISSION_NOT_FOUND if entity_type == "Submission" else ErrorCode.SAMPLE_NOT_FOUND,
            details={
                "entity_type": entity_type,
                "entity_id": entity_id
            },
            **kwargs
        )


class DuplicateEntityException(ApplicationException):
    """Duplicate entity."""
    
    def __init__(self, entity_type: str, identifier: str, **kwargs):
        super().__init__(
            message=f"Duplicate {entity_type}: {identifier}",
            code=ErrorCode.DUPLICATE_SUBMISSION,
            details={
                "entity_type": entity_type,
                "identifier": identifier
            },
            **kwargs
        )


class InvalidRequestException(ApplicationException):
    """Invalid request parameters."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_REQUEST,
            details={"field": field} if field else {},
            **kwargs
        )


class OperationFailedException(ApplicationException):
    """Operation failed."""
    
    def __init__(self, operation: str, reason: str, **kwargs):
        super().__init__(
            message=f"Operation '{operation}' failed: {reason}",
            code=ErrorCode.OPERATION_FAILED,
            details={
                "operation": operation,
                "reason": reason
            },
            **kwargs
        )


# Infrastructure Exceptions

class InfrastructureException(BaseException):
    """Base class for infrastructure exceptions."""
    pass


class DatabaseException(InfrastructureException):
    """Database operation failed."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            details={"operation": operation} if operation else {},
            **kwargs
        )


class FileException(InfrastructureException):
    """File operation failed."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.FILE_NOT_FOUND,
            details={"file_path": file_path} if file_path else {},
            **kwargs
        )


class PDFExtractionException(InfrastructureException):
    """PDF extraction failed."""
    
    def __init__(self, message: str, file_path: str, page: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.PDF_EXTRACTION_ERROR,
            details={
                "file_path": file_path,
                "page": page
            },
            **kwargs
        )


class NetworkException(InfrastructureException):
    """Network operation failed."""
    
    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.NETWORK_ERROR,
            details={"url": url} if url else {},
            **kwargs
        )


class StorageException(InfrastructureException):
    """Storage operation failed."""
    
    def __init__(self, message: str, path: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.STORAGE_ERROR,
            details={"path": path} if path else {},
            **kwargs
        )


# API Exceptions

class APIException(BaseException):
    """Base class for API exceptions."""
    
    @property
    def status_code(self) -> int:
        """Get HTTP status code."""
        code_map = {
            ErrorCode.AUTHENTICATION_FAILED: 401,
            ErrorCode.AUTHORIZATION_FAILED: 403,
            ErrorCode.RATE_LIMIT_EXCEEDED: 429,
            ErrorCode.INVALID_API_KEY: 401,
            ErrorCode.SUBMISSION_NOT_FOUND: 404,
            ErrorCode.SAMPLE_NOT_FOUND: 404,
            ErrorCode.INVALID_REQUEST: 400,
            ErrorCode.DUPLICATE_SUBMISSION: 409,
            ErrorCode.SERVICE_UNAVAILABLE: 503,
            ErrorCode.INTERNAL_ERROR: 500,
        }
        return code_map.get(self.code, 500)


class AuthenticationException(APIException):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHENTICATION_FAILED,
            **kwargs
        )


class AuthorizationException(APIException):
    """Authorization failed."""
    
    def __init__(self, message: str = "Authorization failed", resource: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHORIZATION_FAILED,
            details={"resource": resource} if resource else {},
            **kwargs
        )


class RateLimitException(APIException):
    """Rate limit exceeded."""
    
    def __init__(self, limit: int, window: str, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details={
                "limit": limit,
                "window": window
            },
            **kwargs
        )


# System Exceptions

class SystemException(BaseException):
    """Base class for system exceptions."""
    pass


class ConfigurationException(SystemException):
    """Configuration error."""
    
    def __init__(self, message: str, key: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.CONFIGURATION_ERROR,
            details={"key": key} if key else {},
            **kwargs
        )


class DependencyException(SystemException):
    """External dependency error."""
    
    def __init__(self, service: str, message: str, **kwargs):
        super().__init__(
            message=f"Dependency '{service}' error: {message}",
            code=ErrorCode.DEPENDENCY_ERROR,
            details={"service": service},
            **kwargs
        )


class ServiceUnavailableException(SystemException):
    """Service temporarily unavailable."""
    
    def __init__(self, message: str = "Service temporarily unavailable", retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            details={"retry_after": retry_after} if retry_after else {},
            **kwargs
        )
