import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_raw = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sapa_stats")
# Supabase/Heroku usan postgres:// pero SQLAlchemy 2.x requiere postgresql://
DATABASE_URL = _raw.replace("postgres://", "postgresql://", 1) if _raw.startswith("postgres://") else _raw

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
