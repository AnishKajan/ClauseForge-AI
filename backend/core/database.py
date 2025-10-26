"""
Database configuration and connection management
"""

from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
import logging
import asyncio
import os

from .config import settings

logger = logging.getLogger(__name__)


def make_engine(database_url: str, *, use_null_pool: bool | None = None):
    """
    Creates an engine with sane defaults.
    - In tests (ENVIRONMENT=test) or if use_null_pool=True: use NullPool (no pool args).
    - Otherwise: QueuePool with pool_size/max_overflow and pool_pre_ping.
    """
    env = os.getenv("ENVIRONMENT", "").lower()
    null_pool = use_null_pool if use_null_pool is not None else (env == "test")
    
    if null_pool:
        # Do NOT pass pool_size/max_overflow with NullPool
        return create_async_engine(
            database_url,
            poolclass=NullPool,
            future=True,
            echo=settings.DEBUG,
            echo_pool=settings.DEBUG,
        )
    else:
        pool_size = int(os.getenv("DB_POOL_SIZE", str(getattr(settings, 'DATABASE_POOL_SIZE', 5))))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", str(getattr(settings, 'DATABASE_MAX_OVERFLOW', 10))))
        return create_async_engine(
            database_url,
            pool_pre_ping=True,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=3600,   # Recycle connections after 1 hour
            future=True,
            echo=settings.DEBUG,
            echo_pool=settings.DEBUG,
        )


# Create async engine with proper connection pooling
engine = make_engine(settings.DATABASE_URL)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Manual control over flushing
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_org_context(session: AsyncSession, org_id: str):
    """Set organization context for Row Level Security"""
    await session.execute(
        text("SELECT set_config('app.current_org', :org_id, true)"),
        {"org_id": org_id}
    )


async def clear_org_context(session: AsyncSession):
    """Clear organization context"""
    await session.execute(
        text("SELECT set_config('app.current_org', '', true)")
    )


async def check_database_health() -> bool:
    """Check database connectivity and health"""
    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            result = await conn.execute(text("SELECT 1"))
            if result.scalar() != 1:
                return False
            
            # Test extensions
            await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'"))
            await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            
            logger.info("Database health check passed")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def init_db():
    """Initialize database with extensions"""
    try:
        async with engine.begin() as conn:
            # Enable required extensions
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


# Connection pool event listeners for logging
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level settings"""
    if settings.DEBUG:
        logger.debug("New database connection established")


@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout"""
    if settings.DEBUG:
        logger.debug("Connection checked out from pool")


@event.listens_for(Engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin"""
    if settings.DEBUG:
        logger.debug("Connection returned to pool")


# Database session context manager for manual session management
class DatabaseSession:
    """Context manager for database sessions with org context"""
    
    def __init__(self, org_id: str = None):
        self.org_id = org_id
        self.session = None
    
    async def __aenter__(self) -> AsyncSession:
        self.session = AsyncSessionLocal()
        if self.org_id:
            await set_org_context(self.session, self.org_id)
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()


# Utility functions for testing
async def create_test_session() -> AsyncSession:
    """Create a test database session"""
    return AsyncSessionLocal()


async def reset_database():
    """Reset database for testing (drops all tables)"""
    if settings.ENVIRONMENT != "test":
        raise RuntimeError("Database reset only allowed in test environment")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database reset completed")