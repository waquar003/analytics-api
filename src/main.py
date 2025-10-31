from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.limiter import limiter  
from src.db import create_db_and_tables
from src.api import projects, events
from src.kafka_producer import (
    create_kafka_producer,
    close_kafka_producer,
    set_kafka_producer
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")

    # Initialize db
    print("Initializing database...")
    create_db_and_tables()
    print("Database initailization completed.")

    # Initialize Kafka Producer
    print("Initializing Kafka Producer...")
    producer = create_kafka_producer()
    set_kafka_producer(producer)
    print("Kafka initialized.")
    yield
    print("Application shutdown.")

    # Close Kafka Producer
    print("Closign Kafka Produver...")
    close_kafka_producer()
    print("Kafka Producer closed.")

app = FastAPI(
    title="Analytics API",
    lifespan=lifespan
)

# Initialize the limiter with app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(projects.router)
app.include_router(events.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Analytics API"}