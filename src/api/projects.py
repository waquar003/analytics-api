from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
import secrets
import uuid
from sqlalchemy.exc import IntegrityError

from src.db import get_session
from src.models import (
    Project, 
    ProjectCreate,
    RegisteredEvent,
    RegisteredEventCreate,
    RegisteredEventRead
)
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
    except IntegrityError as ie:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project creation failed due to integrity error: {ie}"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {e}")
    
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

@router.post(
    "/events",
    response_model=RegisteredEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new event type for your project"
)
def register_event_for_project(
    event_data: RegisteredEventCreate,
    project: Project = Depends(get_project_from_secret_key),
    session: Session = Depends(get_session)
):
    """
    Register a new event type (e.g. 'signup', 'purchase') for your project.
    This allows tracking of only approved event types.
    """

    existing = session.exec(
        select(RegisteredEvent).where(
            RegisteredEvent.project_id == project.id,
            RegisteredEvent.event_name == event_data.event_name
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event '{event_data.event_name}' is already registered for this project."
        )
    
    db_event = RegisteredEvent.model_validate(
        event_data,
        update={"project_id": project.id}
    )

    try:
        session.add(db_event)
        session.commit()
        session.refresh(db_event)
    except IntegrityError as ie:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integrity conflict: {ie}. Event '{event_data.event_name}' may already be registered."
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while registering the event: {e}"
        )
    
    return db_event


@router.get(
    "/events",
    response_model=List[RegisteredEventRead],
    summary="List all registered event types for your project"
)
def get_registered_events_for_project(
    project: Project = Depends(get_project_from_secret_key),
    session: Session = Depends(get_session)
):
    """
    Retrieve all registered event types for your project.
    """

    events = session.exec(
        select(RegisteredEvent).where(
            RegisteredEvent.project_id == project.id
        )
    ).all()

    return events


@router.delete(
    '/events/{event_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a registered event type from your project"
)
def delete_registered_event(
    event_id: uuid.UUID,
    project: Project = Depends(get_project_from_secret_key),
    session: Session = Depends(get_session)
):
    """
    Delete a registered event type from your project.
    """

    db_event = session.get(RegisteredEvent, event_id)

    if not db_event or db_event.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registered event not found for this project."
        )
    
    try:
        session.delete(db_event)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the event: {e}"
        )
    
    return None