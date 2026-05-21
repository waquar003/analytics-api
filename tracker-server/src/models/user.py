import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
if TYPE_CHECKING:
    from .project import Project
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy.dialects.postgresql import JSONB

class User(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    projects: List["Project"] = Relationship(back_populates="user")

    refresh_token: Optional[str] = Field(default=None, nullable=True)

class UserCreate(SQLModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    created_at: datetime