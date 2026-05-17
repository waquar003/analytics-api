from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.models.event import AnalyticsEvent
from src.api.security import get_current_user
from src.models.user import User
from sqlmodel import Session, select
import secrets
import uuid
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from src.db import engine
from sqlmodel import text

from src.db import get_session
from src.models import (
    Project, 
    ProjectCreate,
    RegisteredEvent,
    RegisteredEventCreate,
    RegisteredEventRead
)
from src.api import get_project_from_secret_key
from src.worker.cache import SchemaCache

router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)

cache = SchemaCache()

@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
        allowed_origins=project_data.allowed_origins,
        user_id=current_user.id
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

@router.post("/{project_id}/regenerate-key", response_model=Project)
def regenerate_public_api_key(
    project_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerates the PUBLIC API key for your project.
    This invalidates the old key immediately.
    Use this if your key has been exposed or spammed.
    """
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_public_key = f"pub_{secrets.token_hex(16)}"
    project.public_api_key = new_public_key
    
    session.add(project)
    session.commit()
    session.refresh(project)
    
    return project

@router.post(
    "/{project_id}/events",
    response_model=RegisteredEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new event type for your project"
)
def register_event_for_project(
    project_id: uuid.UUID,
    event_data: RegisteredEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Register a new event type (e.g. 'signup', 'purchase') for your project.
    This allows tracking of only approved event types.
    """

    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

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
        cache.invalidate(project.id)
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
    '/{project_id}/events/{event_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a registered event type from your project"
)
def delete_registered_event(
    project_id: uuid.UUID,
    event_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a registered event type from your project.
    """

    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or access denied")

    db_event = session.get(RegisteredEvent, event_id)

    if not db_event or db_event.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registered event not found for this project."
        )
    
    try:
        session.delete(db_event)
        session.commit()
        cache.invalidate(project.id)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the event: {e}"
        )
    
    return None

@router.get("/all", response_model=List[Project])
def list_all_projects(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    statement = select(Project).where(Project.user_id == current_user.id)
    projects = session.exec(statement).all()
    return projects


@router.patch("/{project_id}/whitelist", response_model=Project)
def update_whitelisted_domains(
    project_id: uuid.UUID,
    domains: List[str],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.allowed_origins = domains
    session.add(project)
    session.commit()
    session.refresh(project)
    
    return project


@router.get("/{project_id}/events", response_model=List[RegisteredEventRead])
def get_registered_events_for_project(
    project_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    events = session.exec(
        select(RegisteredEvent).where(RegisteredEvent.project_id == project_id)
    ).all()

    return events


@router.get("/{project_id}/events/received", response_model=List[AnalyticsEvent])
def get_received_events(
    project_id: uuid.UUID,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    events = session.exec(
        select(AnalyticsEvent)
        .where(AnalyticsEvent.project_id == project_id)
        .order_by(AnalyticsEvent.timestamp.desc(), AnalyticsEvent.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return events

class TimeBucket(str, Enum):
    minute = "1 minute"
    hour = "1 hour"
    day = "1 day"
    week = "1 week"
    month = "1 month"

class GroupBy(str, Enum):
    url = "url"
    event_type = "event_type"
    session_id = "session_id"
    user_id = "user_id"

@router.get("/{project_id}/analytics/summary")
def get_analytics(
    project_id: uuid.UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    time_bucket: Optional[TimeBucket]= Query(None),
    group_by: GroupBy = Query(GroupBy.event_type),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now(timezone.utc)
    end_date_to_use = end_date or now
    start_date_to_use = start_date or (end_date_to_use - timedelta(days=1))
    
    time_bucket_to_use = time_bucket
    if not time_bucket_to_use:
        time_delta = end_date_to_use - start_date_to_use
        if time_delta <= timedelta(days=2):
            time_bucket_to_use = TimeBucket.hour
        else:
            time_bucket_to_use = TimeBucket.day

    # Safe Dynamic SQL construction matching your execution engine
    full_query = f"""
        SELECT
            time_bucket(:time_bucket_str, timestamp) AS bucket,
            {group_by.value} AS dimension, 
            COUNT(*) AS count
        FROM analyticsevent
        WHERE project_id = :project_id AND timestamp BETWEEN :start_date AND :end_date
        GROUP BY bucket, {group_by.value}
        ORDER BY bucket DESC, count DESC;
    """
    
    
    with Session(engine) as raw_session:
        results = raw_session.exec(text(full_query), params={
            "project_id": project.id,
            "start_date": start_date_to_use,
            "end_date": end_date_to_use,
            "time_bucket_str": time_bucket_to_use.value
        }).all()
        
    return [{"bucket": r[0], "dimension": r[1], "count": r[2]} for r in results]