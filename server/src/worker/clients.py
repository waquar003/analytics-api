import logging
import time

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

from src.config import settings
from src.worker.utils import is_shutdown_requested

logger = logging.getLogger("AnalyticsWorker.Clients")

def create_consumer() -> KafkaConsumer:
    """Connects to Kafka as a consumer, with retries."""
    logger.info("Attempting to connect Kafka Consumer...")
    while not is_shutdown_requested():
        try:
            consumer = KafkaConsumer(
                settings.KAFKA_MAIN_TOPIC,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP_ID,
                enable_auto_commit=False, 
                value_deserializer=lambda v: v.decode('utf-8'),
                auto_offset_reset='earliest',
                max_poll_records=settings.WORKER_MAX_POLL_RECORDS,
                client_id="analytics-worker-consumer"
            )
            logger.info("Kafka Consumer connection ESTABLISHED.")
            return consumer
        except NoBrokersAvailable:
            logger.warning("Kafka brokers not available. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Failed to create Kafka Consumer: {e}. Retrying in 5s...")
            time.sleep(5)
    
    logger.info("Shutdown requested during consumer creation.")

def create_dlq_producer() -> KafkaProducer:
    """Connects to Kafka as a producer for the DLQ, with retries."""
    logger.info("Attempting to connect Kafka DLQ Producer...")
    while not is_shutdown_requested():
        try:
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v,
                retries=5,
                acks='all',
                client_id="analytics-worker-dlq-producer"
            )
            logger.info("Kafka DLQ Producer connection ESTABLISHED.")
            return producer
        except NoBrokersAvailable:
            logger.warning("Kafka brokers not available (for DLQ). Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Failed to create Kafka DLQ Producer: {e}. Retrying in 5s...")
            time.sleep(5)
    
    logger.info("Shutdown requested during DLQ producer creation.")