from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    """Configuration settings for the application, loaded from .env file."""
    
    # Application Settings
    PORT: int = 8000

    # Database configuration
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int
    DATABASE_URL: str

    # Rate limiting
    DEFAULT_RATELIMIT: str = "1000/minute"
    TRACK_ENDPOINT_RATELIMIT: str = "10/second"

    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:29092"
    KAFKA_MAIN_TOPIC: str = "analytics_events"
    KAFKA_DLQ_TOPIC: str = "analytics_events_dlq"

    class Config:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore" # Ignore extra fields from .env

# Create a single, globally importable settings instance
settings = Settings()