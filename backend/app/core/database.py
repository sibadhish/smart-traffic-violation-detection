from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from backend.app.core.config import settings

# Async engine (for FastAPI endpoints)
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine (for Celery workers)
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=settings.DEBUG)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


def get_sync_db() -> Session:
    """Get a synchronous DB session (for Celery tasks)."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
