from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
import secrets

from src.db import get_session
from src.models import Project, ProjectCreate
from src.api import get_project_from_secret_key

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

@router.get("/", response_model=Project)
def get_my_project_details(
    project: Project = Depends(get_project_from_secret_key)
):
    """
    Get the details for the project associated with your Secret Key.
    """
    return project

@router.post("/regenerate-key", response_model=Project)
def regenerate_public_api_key(
    project: Project = Depends(get_project_from_secret_key),
    session: Session = Depends(get_session)
):
    """
    Regenerates the PUBLIC API key for your project.
    This invalidates the old key immediately.
    Use this if your key has been exposed or spammed.
    """
    new_public_key = f"pub_{secrets.token_hex(16)}"
    project.public_api_key = new_public_key
    
    session.add(project)
    session.commit()
    session.refresh(project)
    
    return project