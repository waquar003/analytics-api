from sqlmodel import create_engine, Session
from src.config import settings

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)

def get_session():
    """
    FastAPI Dependency that provides a database session per request.
    """
    with Session(engine) as session:
        yield session