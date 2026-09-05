from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.mongodb import get_database
from app.db.redis import get_redis
from app.db.repositories.workflow import WorkflowRepository

from app.routers.workflows import router as workflow_router
from app.routers.webhooks import router as webhook_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    WorkflowRepository().create_indexes()
    yield

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)
app.include_router(workflow_router)
app.include_router(webhook_router)


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