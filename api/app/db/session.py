from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables exist for in-memory or demo databases used during tests/demos.
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    # Fall back to per-table creation for demo/local environments when a dialect-specific
    # issue arises. Real deployments should use migration scripts instead.
    for tbl in Base.metadata.sorted_tables:
        try:
            tbl.create(bind=engine, checkfirst=True)
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
