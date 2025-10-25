from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session

from src.db import engine
from src.models import Project, AnalyticsEvent, EventCreate
from src.api.security import get_project_for_tracking

# Create an APIRouter
router = APIRouter(
    tags=["Events"]
)

# --- Background Task Function ---
def _log_event_to_db(event_data: EventCreate, project_id: int):
    """
    This function runs in the background.
    It creates its own database session.
    """
    with Session(engine) as session:
        db_event = AnalyticsEvent.model_validate(
            event_data, 
            update={"project_id": project_id}
        )
        session.add(db_event)
        session.commit()

# --- API Endpoints ---

@router.post("/track", status_code=202)
def track_event(
    event_data: EventCreate,
    background_tasks: BackgroundTasks,
    project: Project = Depends(get_project_for_tracking)
):
    """
    Endpoint to log a new analytics event.
    This is ASYNCHRONOUS: it returns 202 immediately
    and adds the DB write to a background task.
    """
    # Add the DB write to the background queue
    background_tasks.add_task(
        _log_event_to_db, 
        event_data=event_data, 
        project_id=project.id
    )
    
    return {"message": "Event accepted"}