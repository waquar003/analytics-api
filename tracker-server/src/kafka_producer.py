import logging
import json
import time
import asyncio
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from src.config import settings

logger =  logging.getLogger("KafkaProducer")
logging.basicConfig(level=logging.INFO)

# Singleton instance of the producer used globally 
_producer_instance = {"producer": None}

def create_kafka_producer() -> AIOKafkaProducer:
    """
    Create and returns a KafkaProducer instance.
    Include retry logic to handle broker startup delays.
    """
    logger.info("Attempting to create KafkaProducer...")
    producer = AIOKafkaProducer(
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer = lambda v: json.dumps(v).encode('utf-8'),
        retry_backoff_ms = 1000,
        acks = 'all',
        client_id = 'analytics-tracker-asycn-producer'
    )
            

    asyncio.create_task(start_producer_safely(producer))
    return producer


async def start_producer_safely(producer: AIOKafkaProducer):
    while True:
        try:
            await producer.start()
            logger.info("Async AIOKafkaProducer connection pool Established")
            break
        except KafkaConnectionError:
            logger.warning("Kafak cluster broker unavailable")
            await asyncio.sleep(5)


def get_kafka_producer() -> AIOKafkaProducer:
    """
    Return the singleton KafkaProducer instance.
    """

    # This is a fallback mechanism kafka will be initialized in the app file.
    if _producer_instance["producer"] is None:
        logger.warning("KafkaProducer not initialized. Initializing now...")
        _producer_instance["producer"] = create_kafka_producer()

    return _producer_instance["producer"]

def set_kafka_producer(producer: AIOKafkaProducer):
    """Sets the global producer instance"""
    _producer_instance["producer"]=producer


async def close_kafka_producer():
    """
    Flush and closes the singleton KafkaProducer connection.
    """

    producer = _producer_instance["producer"]
    if producer:
        logger.info("Closing active AIOKafkaProducer instance connections..")
        await producer.stop()
        _producer_instance["producer"] = None
        logger.info("KafkaProducer Closed.")