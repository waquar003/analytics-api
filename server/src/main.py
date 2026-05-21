from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.limiter import limiter  
from src.api import auth
from src.api import projects

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Administrative Application Server startup...")
    yield
    print("Administrative Application Server shutdown.")

app = FastAPI(
    title="Analytics Managemennt API",
    lifespan=lifespan
)

# Initialize the limiter with app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(projects.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Analytics API Management"}