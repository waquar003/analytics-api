from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text
from src.models import *
from src.config import settings

# Get the DATABASE_URL from our centralized settings
DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    print("Creating database and tables...")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        try:
            session.exec(
                text("SELECT create_hypertable('analyticsevent', 'timestamp', if_not_exists => TRUE);")
            )
            session.commit()
            print("Hypertable 'analyticsevent' created or already exists.")
        except Exception as e:
            print(f"Error creating hypertable: {e}")
            print("Please ensure the TimescaleDB extension is enabled in your database.")
            session.rollback()

def get_session():
    """
    FastAPI Dependency that provides a database session per request.
    """
    with Session(engine) as session:
        yield session