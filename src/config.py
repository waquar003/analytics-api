from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Configuration settings for the application."""
    
    # Database configuration
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int

    # Application configuration
    PORT: int

    DATABASE_URL: str = ""  # Default to empty, will be constructed if not provided

    class Config:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        env_file_encoding = 'utf-8'
        extra = "forbid"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            

settings = Settings()
