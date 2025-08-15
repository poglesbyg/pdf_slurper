"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from dataclasses import dataclass

T = TypeVar('T')
ID = TypeVar('ID')


@dataclass
class Pagination:
    """Pagination parameters."""
    offset: int = 0
    limit: int = 100
    
    @property
    def skip(self) -> int:
        """Alias for offset."""
        return self.offset


@dataclass
class Page(Generic[T]):
    """Page of results."""
    items: List[T]
    total: int
    offset: int
    limit: int
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.offset + len(self.items) < self.total
    
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.offset > 0
    
    @property
    def page_number(self) -> int:
        """Get current page number (1-based)."""
        return (self.offset // self.limit) + 1
    
    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        return (self.total + self.limit - 1) // self.limit


class Repository(ABC, Generic[T, ID]):
    """Base repository interface."""
    
    @abstractmethod
    async def get(self, id: ID) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        pagination: Optional[Pagination] = None
    ) -> List[T]:
        """Get all entities."""
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save entity (create or update)."""
        pass
    
    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    async def exists(self, id: ID) -> bool:
        """Check if entity exists."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Count total entities."""
        pass
