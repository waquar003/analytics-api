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
    and sends the event to a Kafka topic for processing.
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

    event_data_dict = event_data.model_dump()
    
    # Ensure the properties dictionary exists
    if event_data_dict.get("properties") is None:
        event_data_dict["properties"] = {}
        
    event_data_dict["properties"]["ip_address"] = ip_address
    event_data_dict["properties"]["user_agent"] = user_agent
    event_data_dict["properties"]["referer"] = referer
    
    # Constructing message
    message = {
        'project_id': str(project.id),
        'event_data': event_data_dict,
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