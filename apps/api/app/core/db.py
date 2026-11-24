from sqlalchemy import create_engine
from sqlalchemy.exc import ArgumentError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def database_url_for_runtime(database_url: str):
    try:
        url = make_url(database_url)
    except ArgumentError:
        # SQLAlchemy includes the supplied value in its parse error. Never let a
        # malformed deployment secret reach runtime logs.
        raise ValueError("DATABASE_URL must be a valid SQLAlchemy connection URL") from None
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


runtime_database_url = database_url_for_runtime(settings.database_url)
connect_args = {"check_same_thread": False} if runtime_database_url.drivername == "sqlite" else {}
engine = create_engine(runtime_database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
