from fastapi import APIRouter, Depends, BackgroundTasks, Query, status
from sqlmodel import Session, text
from datetime import datetime
from typing import List, Optional
from enum import Enum
import uuid

from src.db import engine
from src.models import Project, AnalyticsEvent, EventCreate
from src.api.security import get_project_for_tracking, get_project_from_secret_key

# Create an APIRouter
router = APIRouter(
    tags=["Events"]
)

# --- Background Task Function ---
def _log_event_to_db(event_data: EventCreate, project_id: uuid.UUID):
    """
    This function runs in the background.
    It creates its own database session.
    """
    event_dict = event_data.model_dump()
    event_dict["project_id"] = project_id
    
    db_event = AnalyticsEvent.model_validate(event_dict)

    with Session(engine) as session:
        session.add(db_event)
        session.commit()

# --- API Endpoints ---

@router.post("/track", status_code=status.HTTP_202_ACCEPTED)
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


# Create Enums for safe, whitelisted query parameters to prevent SQL injection
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

@router.get("/analytics") 
def get_analytics(
    project: Project = Depends(get_project_from_secret_key),
    start_date: Optional[datetime] = Query(None, description="Start of the time range"),
    end_date: Optional[datetime] = Query(None, description="End of the time range"),
    time_bucket: TimeBucket = Query(TimeBucket.day, description="Interval to bucket data by"),
    group_by: GroupBy = Query(GroupBy.url, description="Dimension to group results by"),
    event_types: Optional[List[str]] = Query(None, description="Filter by one or more event types"),
    url: Optional[str] = Query(None, description="Filter by a specific URL")
):
    """
    Get powerful, flexible analytics for your project.
    
    This endpoint allows you to 'slice and dice' your data by:
    - Defining a time range (start_date, end_date)
    - Bucketing the data (time_bucket)
    - Grouping by a dimension (group_by)
    - Filtering by events or URLs
    """
    
    # Building SQL query dynamically 
    # Build SELECT clause
    select_clause = f"""
        SELECT
            time_bucket(:time_bucket_str, timestamp) AS bucket,
            {group_by.value} AS dimension, 
            COUNT(*) AS count
    """
    from_clause = "FROM analyticsevent"
    
    # Build WHERE clauses and parameters safely
    where_clauses = ["project_id = :project_id", "timestamp BETWEEN :start_date AND :end_date"]
    params = {
        "project_id": project.id,
        "start_date": start_date,
        "end_date": end_date,
        "time_bucket_str": time_bucket.value 
    }
    
    if event_types:
        where_clauses.append("event_type = ANY(:event_types)")
        params["event_types"] = event_types
        
    if url:
        where_clauses.append("url = :url")
        params["url"] = url

    where_string = f"WHERE {' AND '.join(where_clauses)}"
    
    # Build GROUP BY clause
    # We can safely use group_by.value because it's from our whitelisted Enum
    group_by_clause = f"GROUP BY bucket, {group_by.value}"
    
    order_by_clause = "ORDER BY bucket DESC, count DESC"
    
    # Combine and execute the full query
    full_query = f"""
        {select_clause}
        {from_clause}
        {where_string}
        {group_by_clause}
        {order_by_clause};
    """
    
    with Session(engine) as session:
        results = session.exec(text(full_query), params=params).all()
        
    summary = [
        {"bucket": r[0], group_by.value: r[1], "count": r[2]} 
        for r in results
    ]
    return summary