from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings
import importlib.util


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:password@localhost:5432/beauty_pos"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()

database_url = settings.database_url
if database_url.startswith("postgresql://") and importlib.util.find_spec("psycopg2") is None:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=280)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
