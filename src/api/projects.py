from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
import secrets

from src.db import get_session
from src.models import Project, ProjectCreate

router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)

@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate, 
    session: Session = Depends(get_session)
):
    """
    Create a new project.
    Generates a unique public and secret API key.
    """
    # Generate secure, random API keys
    public_key = f"pub_{secrets.token_hex(16)}"
    secret_key = f"sec_{secrets.token_hex(16)}"
    
    project = Project(
        name=project_data.name, 
        public_api_key=public_key,
        secret_api_key=secret_key,
        allowed_origins=project_data.allowed_origins
    )
    
    try:
        session.add(project)
        session.commit()
        session.refresh(project)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Project id or key already exists. Error: {e}")
        
    return project