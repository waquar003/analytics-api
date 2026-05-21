import logging
from fastapi import (
    APIRouter, 
    Depends,
    Request, 
    status,
    HTTPException
)
from aiokafka import AIOKafkaProducer
from datetime import datetime, timezone

from src.kafka_producer import get_kafka_producer
from src.models import Project, EventCreate
from src.api.security import get_project_for_tracking
from src.limiter import limiter
from src.config import settings


router = APIRouter(prefix="/events", tags=["Telemetry Ingestion"])
logger = logging.getLogger("TrackerServer.Events")

@router.post("/track", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.TRACK_ENDPOINT_RATELIMIT)
async def track_event(
    request: Request,
    event_data: EventCreate,
    project: Project = Depends(get_project_for_tracking),
    producer: AIOKafkaProducer = Depends(get_kafka_producer)
):
    """Stateless endpoint takes payload records and streams them to Kafka logs instantly"""

    try:
        ip_address = request.client.host if request.client else "unknown"
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
        'server_timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Send to Kafka
    try:
        await producer.send_and_wait(
            settings.KAFKA_MAIN_TOPIC,
            value = message
        )
    except Exception as e:
        logger.error(f'CRITICAL: Failed to send event to Kafka: {e}')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Event processin g service is temporily unavailable. Please try aagin later.'
        )
    
    return {"status": "queued", "message": "Event payload accepted"}