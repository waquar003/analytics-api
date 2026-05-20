from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.api import events
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.limiter import limiter
from src.kafka_producer import (
    create_kafka_producer,
    close_kafka_producer,
    set_kafka_producer
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Tracker Server Starting up...")

    # Initialize Kafka Producer
    print("Initializing Kafka Producer...")
    producer = create_kafka_producer()
    set_kafka_producer(producer)
    print("Kafka initialized.")
    yield
    print("Tracker Server shutdown.")

    # Close Kafka Producer
    print("Closign Kafka Produver...")
    await close_kafka_producer()
    print("Kafka Producer closed.")

app = FastAPI(
    title="Analytics Ingestion Tracker API",
    lifespan=lifespan
)

# Initialize the limiter with app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["X-API-KEY", "Content-Type"],
)

app.include_router(events.router)


@app.get("/healthz")
def health_check():
    return {
        "status": "healthy",
        "service": "tracker-ingestion"
    }