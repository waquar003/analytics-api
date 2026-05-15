import uuid
from sqlmodel import Field, SQLModel, Column, Relationship
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import JSONB
if TYPE_CHECKING:
    from .user import User

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

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, nullable=False)
    user: "User" = Relationship(back_populates='projects')

class ProjectCreate(SQLModel):
    """
    Data model for the API when creating a new project.
    """
    name: str
    # Allow setting the whitelist on creation
    allowed_origins: Optional[List[str]] = None