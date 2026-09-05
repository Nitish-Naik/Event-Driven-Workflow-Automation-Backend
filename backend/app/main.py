from fastapi import FastAPI

from app.config import settings
from app.db.mongodb import get_database
from app.db.redis import get_redis


app = FastAPI(
    title=settings.app_name,
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