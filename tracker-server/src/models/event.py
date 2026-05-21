import uuid
from sqlmodel import Field, SQLModel, Column
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.dialects.postgresql import JSONB

class AnalyticsEvent(SQLModel, table=True):
    """
    Represents a single tracked event.
    This will be converted to a TimescaleDB Hypertable.
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True, 
        index=True, 
        nullable=False
    )
    
    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    
    
    event_type: str = Field(index=True, default="pageview")
    url: str = Field(index=True)
    
    session_id: Optional[str] = Field(default=None, index=True)
    user_id: Optional[str] = Field(default=None, index=True)

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        nullable=False,
        index=True
    )
    
    # Flexible field for any other data (e.g., "plan_type", "video_id")
    properties: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSONB))

class EventCreate(SQLModel):
    """
    The data model the client sends to the /track endpoint.
    """
    event_type: str = "pageview"
    url: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = {}