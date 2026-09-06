import json
import time

class RetryQueue:
    QUEUE_NAME = "sentry:retries"

    def __init__(self, redis_client):
        self.redis = redis_client

    def schedule(self, event_id: str, run_id: str, attempt: int, delay: float):
        message = {
            "event_id": event_id,
            "run_id": run_id,
            "attempt": attempt,
        }

        execute_at = time.time() + delay

        self.redis.zadd(
            self.QUEUE_NAME,
            {
                json.dumps(message): execute_at,
            }
        )


    def pop_due(self):
        now = time.time()

        items = self.redis.zrangebyscore(
            self.QUEUE_NAME,
            0,
            now,
            start=0,
            num=1,
        )

        if not items:
            return None
        
        message = items[0]

        self.redis.zrem(
            self.QUEUE_NAME,
            message,
        )

        return json.loads(message)