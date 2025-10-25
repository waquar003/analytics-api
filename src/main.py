from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db import create_db_and_tables
from src.api import projects, events

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    create_db_and_tables()
    yield
    print("Application shutdown.")

# Create the main FastAPI app instance
app = FastAPI(
    title="Analytics API",
    lifespan=lifespan
)

# Routers
app.include_router(projects.router)
app.include_router(events.router)

# Add a simple root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Analytics API"}