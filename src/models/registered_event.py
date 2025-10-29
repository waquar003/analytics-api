import uuid
from sqlmodel import SQLModel, Field, UniqueConstraint
from typing import Optional
import datetime

class RegisteredEventBase(SQLModel):
    """
    Base model for a user-registered event type.
    """

    event_name: str = Field(
        ...,
        index=True,
        description="The name of the event.( e.g., 'signup', 'purchase' )"
    )

class RegisteredEvent(RegisteredEventBase, table=True):
    """
    Database model for a user-registered event type.
    Represents the "allow-list" of events that can be tracked for a project.
    """

    __tablename__ = "registered_event"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )

    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "event_name", name="unique_project_event_name"),
    )


class RegisteredEventCreate(RegisteredEventBase):
    """
    Pydantic model for creating a new registered event.
    Used when a client registers a new event type for a project.
    """
    pass

class RegisteredEventRead(RegisteredEventBase):
    """
    Pydantic model for reading a registered event.
    Used when returning registered event data to the client.
    """
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime.datetime