"""Configuration settings using Pydantic."""

from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    # Application
    app_name: str = Field(
        default="PDF Slurper",
        description="Application name"
    )
    app_version: str = Field(
        default="2.0.0",
        description="Application version"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite:///./pdf_slurper.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries"
    )
    database_pool_size: int = Field(
        default=5,
        description="Database connection pool size"
    )
    
    # Storage
    data_dir: Path = Field(
        default=Path("/app/data"),
        description="Data directory path"
    )
    upload_dir: Path = Field(
        default=Path("/app/data/uploads"),
        description="Upload directory path"
    )
    max_upload_size: int = Field(
        default=100_000_000,  # 100MB
        description="Maximum upload size in bytes"
    )
    
    # PDF Processing
    pdf_max_pages: int = Field(
        default=1000,
        description="Maximum pages to process"
    )
    pdf_extract_timeout: int = Field(
        default=300,  # 5 minutes
        description="PDF extraction timeout in seconds"
    )
    pdf_parallel_tables: bool = Field(
        default=True,
        description="Process tables in parallel"
    )
    
    # Quality Control
    qc_min_concentration: float = Field(
        default=10.0,
        description="Minimum concentration (ng/µL)"
    )
    qc_min_volume: float = Field(
        default=20.0,
        description="Minimum volume (µL)"
    )
    qc_min_quality_ratio: float = Field(
        default=1.8,
        description="Minimum A260/A280 ratio"
    )
    qc_auto_apply: bool = Field(
        default=False,
        description="Automatically apply QC on import"
    )
    
    # API
    api_prefix: str = Field(
        default="/api/v1",
        description="API prefix"
    )
    api_docs_enabled: bool = Field(
        default=True,
        description="Enable API documentation"
    )
    api_cors_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    api_rate_limit: int = Field(
        default=100,
        description="API rate limit per minute"
    )
    
    # Security
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    jwt_expiration_minutes: int = Field(
        default=30,
        description="JWT token expiration in minutes"
    )
    
    # Server
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8080,
        description="API server port"
    )
    web_port: int = Field(
        default=3000,
        description="Web UI server port"
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes"
    )
    
    # Logging
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Log level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path"
    )
    
    # OpenShift specific
    openshift_build_name: Optional[str] = Field(
        default=None,
        env="OPENSHIFT_BUILD_NAME",
        description="OpenShift build name"
    )
    openshift_build_namespace: Optional[str] = Field(
        default=None,
        env="OPENSHIFT_BUILD_NAMESPACE",
        description="OpenShift namespace"
    )
    
    @field_validator("data_dir", "upload_dir", "log_file", mode="before")
    @classmethod
    def expand_path(cls, v):
        """Expand path with home directory."""
        if v is None:
            return v
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser().resolve()
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v, info):
        """Adjust database URL based on environment."""
        if v.startswith("sqlite://"):
            # Ensure absolute path for SQLite
            path = v.replace("sqlite:///", "").replace("./", "")
            if not path.startswith("/"):
                # Only add data_dir if path is relative
                data_dir = info.data.get("data_dir", Path("data"))
                # Make sure we don't duplicate the path
                if str(data_dir) not in path:
                    path = str(data_dir / path)
                v = f"sqlite:///{path}"
        return v
    
    @field_validator("workers")
    @classmethod  
    def validate_workers(cls, v, info):
        """Adjust workers based on environment."""
        env = info.data.get("environment", Environment.DEVELOPMENT)
        if env == Environment.DEVELOPMENT:
            return 1  # Single worker for development
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
