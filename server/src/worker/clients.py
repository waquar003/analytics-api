import logging
import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from src.config import settings

logger = logging.getLogger("AnalyticsWorker.Clients")

async def create_consumer() -> AIOKafkaConsumer:
    """Connects to Kafka as a consumer, with retries."""
    logger.info("Attempting to initialize Async AIOKafkaConsumer")
    while True:
        try:
            consumer = AIOKafkaConsumer(
                settings.KAFKA_MAIN_TOPIC,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP_ID,
                enable_auto_commit=False, 
                value_deserializer=lambda v: v.decode('utf-8'),
                auto_offset_reset='earliest',
                max_poll_records=settings.WORKER_MAX_POLL_RECORDS,
                client_id="analytics-worker-consumer"
            )
            await consumer.start()
            logger.info("Kafka Consumer connection ESTABLISHED.")
            return consumer
        except KafkaConnectionError:
            logger.warning("Kafka brokers not available. Retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Failed to create Kafka Consumer: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

async def create_dlq_producer() -> AIOKafkaProducer:
    """Connects to Kafka as a producer for the DLQ, with retries."""
    logger.info("Attempting to initialize Async AIOKafka DLQ Producer...")
    while True:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v,
                acks='all',
                client_id="analytics-worker-dlq-producer"
            )
            await producer.start()
            logger.info("Kafka DLQ Producer connection ESTABLISHED.")
            return producer
        except KafkaConnectionError:
            logger.warning("Kafka brokers not available (for DLQ). Retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Failed to create Kafka DLQ Producer: {e}. Retrying in 5s...")
            await asyncio.sleep(5)