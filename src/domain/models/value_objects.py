"""Value objects for the domain layer."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, NewType
from datetime import datetime


# Type aliases for IDs
SubmissionId = NewType('SubmissionId', str)
SampleId = NewType('SampleId', str)
UserId = NewType('UserId', str)


class WorkflowStatus(str, Enum):
    """Sample workflow status."""
    RECEIVED = "received"
    PROCESSING = "processing"
    SEQUENCED = "sequenced"
    COMPLETED = "completed"
    FAILED = "failed"
    ON_HOLD = "on_hold"


class QCStatus(str, Enum):
    """Quality control status."""
    PENDING = "pending"
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass(frozen=True)
class Concentration:
    """Concentration measurement value object."""
    value: float
    unit: str = "ng/µL"
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Concentration cannot be negative")
    
    def meets_threshold(self, min_value: float) -> bool:
        """Check if concentration meets minimum threshold."""
        return self.value >= min_value


@dataclass(frozen=True)
class Volume:
    """Volume measurement value object."""
    value: float
    unit: str = "µL"
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Volume cannot be negative")
    
    def meets_threshold(self, min_value: float) -> bool:
        """Check if volume meets minimum threshold."""
        return self.value >= min_value


@dataclass(frozen=True)
class QualityRatio:
    """Quality ratio measurement (e.g., A260/A280)."""
    value: float
    ratio_type: str = "A260/A280"
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Quality ratio cannot be negative")
    
    def is_acceptable(self, min_value: float = 1.8, max_value: float = 2.0) -> bool:
        """Check if ratio is within acceptable range."""
        return min_value <= self.value <= max_value


@dataclass(frozen=True)
class StorageLocation:
    """Storage location value object."""
    freezer: Optional[str] = None
    shelf: Optional[str] = None
    box: Optional[str] = None
    position: Optional[str] = None
    
    @property
    def full_location(self) -> str:
        """Get full location string."""
        parts = []
        if self.freezer:
            parts.append(f"Freezer-{self.freezer}")
        if self.shelf:
            parts.append(f"Shelf-{self.shelf}")
        if self.box:
            parts.append(f"Box-{self.box}")
        if self.position:
            parts.append(f"Pos-{self.position}")
        return " ".join(parts) if parts else "Unknown"
    
    @classmethod
    def from_string(cls, location: str) -> 'StorageLocation':
        """Parse location string into components."""
        parts = {}
        for part in location.split():
            if '-' in part:
                key, value = part.split('-', 1)
                if key.lower() == 'freezer':
                    parts['freezer'] = value
                elif key.lower() == 'shelf':
                    parts['shelf'] = value
                elif key.lower() == 'box':
                    parts['box'] = value
                elif key.lower() in ['pos', 'position']:
                    parts['position'] = value
        return cls(**parts)


@dataclass(frozen=True)
class Barcode:
    """Sample barcode value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Barcode cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Barcode too long")


@dataclass(frozen=True)
class EmailAddress:
    """Email address value object."""
    value: str
    
    def __post_init__(self):
        if '@' not in self.value:
            raise ValueError("Invalid email address")


@dataclass(frozen=True)
class Organism:
    """Source organism value object."""
    species: str
    strain: Optional[str] = None
    tissue: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get full organism description."""
        parts = [self.species]
        if self.strain:
            parts.append(f"strain {self.strain}")
        if self.tissue:
            parts.append(f"from {self.tissue}")
        return " ".join(parts)


@dataclass(frozen=True)
class DateRange:
    """Date range value object."""
    start: datetime
    end: Optional[datetime] = None
    
    def __post_init__(self):
        if self.end and self.end < self.start:
            raise ValueError("End date cannot be before start date")
    
    def contains(self, date: datetime) -> bool:
        """Check if date is within range."""
        if date < self.start:
            return False
        if self.end and date > self.end:
            return False
        return True


@dataclass(frozen=True)
class QualityScore:
    """Quality score value object (0-100)."""
    value: float
    
    def __post_init__(self):
        if not 0 <= self.value <= 100:
            raise ValueError("Quality score must be between 0 and 100")
    
    @property
    def grade(self) -> str:
        """Get letter grade for score."""
        if self.value >= 90:
            return "A"
        elif self.value >= 80:
            return "B"
        elif self.value >= 70:
            return "C"
        elif self.value >= 60:
            return "D"
        else:
            return "F"
    
    @property
    def category(self) -> str:
        """Get quality category."""
        if self.value >= 80:
            return "Excellent"
        elif self.value >= 60:
            return "Good"
        elif self.value >= 40:
            return "Fair"
        else:
            return "Poor"
