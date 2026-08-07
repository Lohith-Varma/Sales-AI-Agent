import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Decide which database URL to use
if settings.USE_SQLITE:
    DATABASE_URL = settings.DATABASE_SQLITE_URL
    # SQLite requires check_same_thread=False for async/websocket scenarios
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
    logger.info(f"Database configuration: Using SQLite database at {DATABASE_URL}")
else:
    DATABASE_URL = settings.DATABASE_URL
    engine_kwargs = {}
    logger.info(f"Database configuration: Using PostgreSQL database")

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for acquiring DB session in FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
