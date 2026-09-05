from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.mongodb import get_database
from app.db.redis import get_redis
from app.db.repositories.workflow import WorkflowRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    WorkflowRepository().create_indexes()
    yield

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)


@app.get("/health")
def health():
    mongo = get_database()
    redis_client = get_redis()

    mongo.command("ping")
    redis_client.ping()

    return {
        "status": "ok",
        "environment": settings.environment,
    }