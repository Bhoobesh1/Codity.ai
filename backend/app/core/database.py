"""
Database engine and session management.

Design note: we use SQLAlchemy's classic (sync) engine + session for now.
Why sync instead of async SQLAlchemy? Because Phase 2's atomic job-claiming
logic relies on explicit, easy-to-reason-about transactions
(SELECT ... FOR UPDATE SKIP LOCKED). Sync sessions make that logic simpler
to write and test correctly first; the API layer can still serve many
concurrent requests fine at this project's scale via FastAPI's threadpool.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # detects dropped connections before using them
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""

    pass


def get_db() -> Generator:
    """
    FastAPI dependency that yields a database session per-request
    and guarantees it's closed afterward, even if an exception occurs.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
