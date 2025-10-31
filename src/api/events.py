import logging
from fastapi import (
    APIRouter, 
    Depends, 
    Query, 
    Request, 
    status,
    HTTPException
)
from kafka import KafkaProducer
from kafka.errors import KafkaError
from sqlmodel import Session, text
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from enum import Enum
import uuid

from src.kafka_producer import get_kafka_producer
from src.db import engine
from src.models import Project, AnalyticsEvent, EventCreate
from src.api.security import get_project_for_tracking, get_project_from_secret_key
from src.limiter import limiter
from src.config import settings

# Create an APIRouter
router = APIRouter(
    tags=["Events"]
)

logger = logging.getLogger("AnalyticsAPI.Events")

# API Endpoints

@router.post("/track", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.TRACK_ENDPOINT_RATELIMIT)
def track_event(
    request: Request,
    event_data: EventCreate,
    # background_tasks: BackgroundTasks,
    project: Project = Depends(get_project_for_tracking),
    producer: KafkaProducer = Depends(get_kafka_producer)
):
    """
    Endpoint to log a new analytics event.
    This is ASYNCHRONOUS: it returns 202 immediately
    and adds the DB write to a background task.
    """

    try:
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        referer = request.headers.get("referer", "unknown")
    except Exception as e:
        logger.warning(f'could not extract request metadata: {e}')
        ip_address = "unknown"
        user_agent = "unknown"
        referer = "unknown"

    # Constructing message
    message = {
        'project_id': str(project.id),
        'event_data': event_data.model_dump(),
        'ip_address': ip_address,
        'user_agent': user_agent,
        'referer': referer,
        'server_timestamp': datetime.utcnow().isoformat()
    }
    
    # Send to Kafka
    try:
        producer.send(
            settings.KAFKA_MAIN_TOPIC,
            value = message
        )
    except KafkaError as e:
        logger.error(f'CRITICAL: Failed to send event to Kafka: {e}')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Event processin g service is temporily unavailable. Please try aagin later.'
        )
    except Exception as e:
        logger.error(f'Unexpected error sendign to Kafka: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred'
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
    time_bucket: Optional[TimeBucket] = Query(None, description="Interval to bucket data by"),
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

    now = datetime.now(timezone.utc)
    end_date_to_use = end_date or now
    start_date_to_use = start_date or (end_date_to_use - timedelta(days=1))
    
    time_bucket_to_use = time_bucket
    if not time_bucket_to_use:
        time_delta = end_date_to_use - start_date_to_use
        if time_delta <= timedelta(days=2):
            time_bucket_to_use = TimeBucket.hour
        elif time_delta <= timedelta(days=31):
            time_bucket_to_use = TimeBucket.day
        elif time_delta <= timedelta(days=90):
            time_bucket_to_use = TimeBucket.week
        else:
            time_bucket_to_use = TimeBucket.month
    
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
        "start_date": start_date_to_use,
        "end_date": end_date_to_use,
        "time_bucket_str": time_bucket_to_use.value 
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