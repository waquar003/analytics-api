import logging
import time
import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from src.config import settings
from src.db import engine as db_engine
from src.worker.clients import create_consumer, create_dlq_producer
from src.worker.processing import process_message_batch
from src.worker.utils import setup_signal_handlers, is_shutdown_requested, touch_healthcheck_file

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger("AnalyticsWorker.Main")



async def main_loop(
    consumer: AIOKafkaConsumer,
    dlq_producer: AIOKafkaProducer,
    db_engine: Engine,
):
    """The consumer mian loop, polling, processing, and committing offsets. And inserting into DB."""
    logger.info("Asynchronous ingestion worker loop started")

    while not is_shutdown_requested():
        try:
            # Poll for a batch of messages wiht a timeout
            batch = await consumer.getmany(timeout_ms=settings.WORKER_POLL_TIMEOUT * 1000, max_records=settings.WORKER_MAX_POLL_RECORDS)
            
            if not batch:
                touch_healthcheck_file() # Confirm liveness 
                await asyncio.sleep(0.1)
                continue # No messages, loop again
                
            logger.info(f"Processing batch with {sum(len(m) for m in batch.values())} messages...")
            
            # Store the starting offsets in case we need to rollback
            start_offsets = {tp: messages[0].offset for tp, messages in batch.items()}

            # Inserting into DB 
            with Session(db_engine) as session:
                # Process the batch
                valid_events, offsets_to_commit = process_message_batch(
                    batch, session, dlq_producer
                )

                # Insert valid events into DB
                if valid_events:
                    try:
                        session.add_all(valid_events)
                        session.commit()
                        logger.info(f"Successfully inserted {len(valid_events)} events into DB.")
                    
                    except OperationalError as e:
                        logger.error(f"Database connection error: {e}. Rewinding batch and retrying...")
                        session.rollback() # Rollback any partial work
                        # Rewind consumer to start offsets of current batch
                        for tp, offset in start_offsets.items():
                            consumer.seek(tp, offset)
                        await asyncio.sleep(10) # Wait for DB to recover
                        continue # Skip commit and healthcheck
                    
                    except Exception as e:
                        logger.error(f"Failed to insert batch into DB (non-retryable): {e}")
                        session.rollback()
                        # Commit the offsets as this batch caused an unrecoverable error

            # Commit offsets after successfully inserting into DB
            if offsets_to_commit:
                await consumer.commit(offsets_to_commit)
                logger.debug("Offsets committed to Kafka.")

            # Signal liveness
            touch_healthcheck_file()

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}. Sleeping for 5s...")
            await asyncio.sleep(5)


# Entry Point
async def async_main():
    logger.info("Starting Analytics Worker...")
    setup_signal_handlers()
    
    consumer = await create_consumer()
    dlq_producer = await create_dlq_producer()

    try:
        await main_loop(consumer, dlq_producer, db_engine)
    except Exception as e:
        logger.error(f"CRITICAL: Main loop exited unexpectedly: {e}")
    finally:
        logger.info("Shutting down worker...")
        await consumer.stop()
        await dlq_producer.stop()
        logger.info("Worker shutdown complete.")

if __name__ == "__main__":
    asyncio.run(async_main())