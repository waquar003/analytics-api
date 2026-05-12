import json
import logging
from typing import Dict, List, Tuple
from uuid import UUID

from kafka import KafkaProducer
from kafka.errors import KafkaError
from kafka.structs import TopicPartition, OffsetAndMetadata
from pydantic import ValidationError
from sqlmodel import Session, select

from src.config import settings
from src.models import AnalyticsEvent, RegisteredEvent
from src.worker.cache import SchemaCache

logger = logging.getLogger("AnalyticsWorker.Processing")

schema_cache = SchemaCache()

def is_event_valid(session: Session, project_id: UUID, event_name: str) -> bool:
    """
    Checks if an event is registered for the project.
    """
    logger.info("Trying")
    try:
        allowed_events = schema_cache.get_allowed_events(session, project_id)
        
        if event_name in allowed_events:
            return True
        else:
            logger.warning(f"Invalid event for project_id {project_id}: '{event_name}'. Dropping.")
            return False
    except Exception as e:
        logger.error(f"Error validating event: {e}. Defaulting to drop.")
        return False


def send_to_dlq(dlq_producer: KafkaProducer, topic: str, value: bytes):
    """Sends a single raw message to the Dead Letter Queue."""
    try:
        dlq_producer.send(topic, value=value)
    except KafkaError as ke:
        logger.error(f"CRITICAL: Failed to send to DLQ: {ke}")


def process_message_batch(
    batch: Dict[TopicPartition, List],
    session: Session,
    dlq_producer: KafkaProducer
) -> Tuple[List[AnalyticsEvent], Dict[TopicPartition, OffsetAndMetadata]]:
    """
    Processes a batch of messages from Kafka.
    Returns a list of valid events to insert and a dict of offsets to commit.
    """
    valid_events_to_insert: List[AnalyticsEvent] = []
    offsets_to_commit: Dict[TopicPartition, OffsetAndMetadata] = {}

    for tp, messages in batch.items():
        for msg in messages:
            try:
                # Parse the message value
                message_data = json.loads(msg.value)
                event_data = message_data.get("event_data", {})
                project_id_str = message_data.get("project_id")
                
                if not project_id_str or not event_data:
                    raise ValueError("Missing project_id or event_data")

                project_id = UUID(project_id_str)
                event_name = event_data.get("event_type", "unknown")

                # Validate schema
                if not is_event_valid(session, project_id, event_name):
                    pass # Drop invalid event
                else:
                    # Create AnalyticsEvent instance
                    properties = event_data.get("properties", {})
                    
                    db_event = AnalyticsEvent(
                        project_id=project_id,
                        event_type=event_name,
                        url=event_data.get("url"),
                        session_id=event_data.get("session_id"),
                        user_id=event_data.get("user_id"),
                        timestamp=message_data.get("server_timestamp"),
                        properties=properties
                    )
                    valid_events_to_insert.append(db_event)

            except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as e:
                # sending "Poison Pill" messages to the DLQ
                logger.error(f"Failed to parse or validate message (Offset {msg.offset}): {e}. Sending to DLQ.")
                send_to_dlq(dlq_producer, settings.KAFKA_DLQ_TOPIC, msg.value)
            
            except Exception as e:
                logger.error(f"Unexpected error processing message (Offset {msg.offset}): {e}. Sending to DLQ.")

            # Always commit the offset, even for dropped/failed messages to avoid stucking in lhte loop
            offsets_to_commit[tp] = OffsetAndMetadata(msg.offset + 1, None, None)

    return valid_events_to_insert, offsets_to_commit