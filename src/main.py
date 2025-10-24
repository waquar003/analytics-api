from typing import Union
from fastapi import FastAPI
from src.config import settings

app = FastAPI()

@app.get("/")
def read_root():
    print(settings.DATABASE_URL)  # Accessing the database URL from settings
    return {"Hello": "Waquar"}