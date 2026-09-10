import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables exist for in-memory or demo databases used during tests/demos.
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:  # pragma: no cover - dialect-specific fallback
    logger.warning("create_all failed (%s); falling back to per-table creation", exc)
    # Fall back to per-table creation for demo/local environments when a dialect-specific
    # issue arises. Real deployments should use migration scripts instead.
    for tbl in Base.metadata.sorted_tables:
        try:
            tbl.create(bind=engine, checkfirst=True)
        except Exception as tbl_exc:  # pragma: no cover - best-effort fallback
            logger.warning("failed to create table %s: %s", tbl.name, tbl_exc)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
