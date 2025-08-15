"""Database connection and session management."""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self, database_url: str, echo: bool = False, pool_size: int = 5):
        """Initialize database.
        
        Args:
            database_url: Database connection URL
            echo: Whether to echo SQL statements
            pool_size: Connection pool size
        """
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        
        # Sync engine and session
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        
        # Async engine and session (if URL supports async)
        self._async_engine: Optional[AsyncEngine] = None
        self._async_session_factory: Optional[sessionmaker] = None
        
        self._is_async = self._check_async_support(database_url)
    
    def _check_async_support(self, url: str) -> bool:
        """Check if database URL supports async operations."""
        # SQLite doesn't support async well, PostgreSQL does
        return "postgresql" in url or "asyncpg" in url
    
    @property
    def engine(self) -> Engine:
        """Get sync database engine."""
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                echo=self.echo,
                pool_size=self.pool_size,
                pool_pre_ping=True  # Verify connections before using
            )
            logger.info(f"Created sync database engine: {self.database_url}")
        return self._engine
    
    @property
    def async_engine(self) -> AsyncEngine:
        """Get async database engine."""
        if not self._is_async:
            raise RuntimeError("Database does not support async operations")
        
        if self._async_engine is None:
            # Convert sync URL to async URL if needed
            async_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            self._async_engine = create_async_engine(
                async_url,
                echo=self.echo,
                pool_size=self.pool_size,
                pool_pre_ping=True
            )
            logger.info(f"Created async database engine: {async_url}")
        return self._async_engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get sync session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                class_=Session,
                expire_on_commit=False
            )
        return self._session_factory
    
    @property
    def async_session_factory(self) -> sessionmaker:
        """Get async session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory
    
    def create_tables(self) -> None:
        """Create all database tables."""
        SQLModel.metadata.create_all(self.engine)
        logger.info("Created database tables")
    
    async def create_tables_async(self) -> None:
        """Create all database tables asynchronously."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Created database tables (async)")
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        SQLModel.metadata.drop_all(self.engine)
        logger.info("Dropped database tables")
    
    async def drop_tables_async(self) -> None:
        """Drop all database tables asynchronously."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        logger.info("Dropped database tables (async)")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session (sync).
        
        Yields:
            Database session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session (async).
        
        Yields:
            Async database session
        """
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Closed sync database engine")
        
        if self._async_engine:
            # Note: In production, use await self._async_engine.dispose()
            logger.info("Async engine should be disposed with await")
    
    async def close_async(self) -> None:
        """Close database connections asynchronously."""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Closed async database engine")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_async()
