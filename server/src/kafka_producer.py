import logging
import json
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from src.config import settings

logger =  logging.getLogger("KafkaProducer")
logging.basicConfig(level=logging.INFO)

# Singleton instance of the producer used globally 
_producer_instance = {"producer": None}

def create_kafka_producer() -> KafkaProducer:
    """
    Create and returns a KafkaProducer instance.
    Include retry logic to handle broker startup delays.
    """
    logger.info("Attempting to create KafkaProducer...")
    producer = None
    while producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer = lambda v: json.dumps(v).encode('utf-8'),
                retries = 5,
                retry_backoff_ms = 1000,
                acks = 'all',
                client_id = 'analytics-api-producer'
            )
            logger.info("KafkaProducer connection ESTABLISHED")
        except NoBrokersAvailable:
            logger.warning("Kafka brokers are not available. Retrying n 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f'Failed to create KafkaProdiver: {e}. Retrying in 5s...')
            time.sleep(5)

    return producer


def get_kafka_producer() -> KafkaProducer:
    """
    Return the singleton KafkaProducer instance.
    """

    # This is a fallback mechanism kafka will be initialized in the app file.
    if _producer_instance["producer"] is None:
        logger.warning("KafkaProducer not initialized. Initializing now...")
        _producer_instance["producer"] = create_kafka_producer()

    return _producer_instance["producer"]

def set_kafka_producer(producer: KafkaProducer):
    """Sets the global producer instance"""
    _producer_instance["producer"]=producer


def close_kafka_producer():
    """
    Flush and closes the singleton KafkaProducer connection.
    """

    producer = _producer_instance["producer"]
    if producer:
        logger.info("Flushing and closign KafkaProducer...")
        producer.flush()
        producer.close()
        _producer_instance["producer"] = None
        logger.info("KafkaProducer Closed.")