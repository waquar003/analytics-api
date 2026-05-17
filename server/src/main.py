from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.api import auth
from src.api import events
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.limiter import limiter  
from src.db import create_db_and_tables
from src.api import projects
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
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def dynamic_cors_handler(request: Request, call_next):
    origin = request.headers.get("origin")
    path = request.url.path

    if request.method == "OPTIONS":
        response = Response(status_code=204)
        if path == "/track":
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
        elif origin == "http://localhost:4200":
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:4200"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            return Response(status_code=400, content="Origin access disallowed by dashboard security matrix")
        return response
    
    response = await call_next(request)

    # Append runtime CORS headers based on targeting route endpoints
    if path == "/track" and origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    elif origin == "http://localhost:4200":
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:4200"
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# Routers
app.include_router(projects.router)
app.include_router(events.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Analytics API"}