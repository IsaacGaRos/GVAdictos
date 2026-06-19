"""Database connection factory supporting SQLite and PostgreSQL.

Use:
    from src.db.database import get_engine, SessionLocal

    engine = get_engine()  # Auto-detects from DATABASE_URL env var
    session = SessionLocal()
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from src.db.models import Base


def get_database_url() -> str:
    """Get database URL from environment or default to SQLite."""
    url = os.getenv("DATABASE_URL", None)

    if url:
        return url

    # Default: SQLite for development
    db_path = os.path.abspath("db/gvadictos.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f"sqlite:///{db_path}"


def get_engine():
    """Create and return database engine.

    Supports:
    - SQLite: sqlite:///./db/gvadictos.sqlite (default)
    - PostgreSQL: postgresql://user:pass@localhost/gvadictos_db
    """
    database_url = get_database_url()

    if database_url.startswith("sqlite"):
        # SQLite configuration
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL configuration
        engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Test connections before using
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        )

    return engine


def init_db():
    """Create all tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Initialized with: {get_database_url()}")


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_session() -> Session:
    """Dependency for FastAPI to get a DB session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
