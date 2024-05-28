"""
Module that provides entry point for the Orders API
"""

from pathlib import Path

import yaml
from fastapi import FastAPI, status
from fastapi.concurrency import asynccontextmanager

from orders_service.api import router
from orders_service.config import get_config
from orders_service.session import begin_session_create_tables, end_session, init_session_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI Lifespan"""

    await begin_session_create_tables()
    yield
    await end_session()


init_session_manager(get_config("orders_service/.env").DATABASE_URL)

app = FastAPI(
    title="Orders API", lifespan=lifespan, debug=True, openapi_url="/openapi/orders.json", docs_url="/docs/orders"
)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health Check"""

    return "Server is running!"


app.include_router(router, tags=["orders"], prefix="/v1")

oas_doc = yaml.safe_load((Path(__file__).parent / "oas.yaml").read_text())

app.openapi = lambda: oas_doc
