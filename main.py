"""
Module providing root endpoint
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def get_root():
    """Root Endpoint"""
    return "Hello Ordering System Microservices"
