import uuid
from server.src.models.user import User, UserToProject
from sqlmodel import Field, SQLModel, Column, Relationship
from typing import Optional, List
from sqlalchemy.dialects.postgresql import JSONB

class Project(SQLModel, table=True):
    """
    Represents a single website or application you are tracking.
    This provides multi-tenancy.
    """

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True, 
        index=True, 
        nullable=False
    )
    name: str
    public_api_key: str = Field(unique=True, index=True)
    secret_api_key: str = Field(unique=True, index=True)
    allowed_origins: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    user: User = Relationship(
        back_populates="projects",
        link_model=UserToProject
    )

class ProjectCreate(SQLModel):
    """
    Data model for the API when creating a new project.
    """
    name: str
    # Allow setting the whitelist on creation
    allowed_origins: Optional[List[str]] = None