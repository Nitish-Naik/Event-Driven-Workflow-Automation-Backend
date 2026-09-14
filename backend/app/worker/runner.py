import asyncio
import logging

from app.queue.event_queue import EventQueue
from app.worker.event_worker import EventWorker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


class WorkerRunner:
    """Long-running process that drains the reliable event queue."""

    def __init__(self, worker=None, queue=None, poll_interval: float = 0.5):
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")
        self.worker = worker if worker is not None else EventWorker()
        self.queue = queue if queue is not None else EventQueue()
        self.poll_interval = poll_interval
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def run_once(self) -> bool:
        retry_processed = await self.worker.process_retry_next_async()
        if retry_processed:
            logger.info("Due workflow retry processed")
            return True

        queued_event = self.queue.reserve()
        if queued_event is None:
            return False

        logger.info(
            "Event reserved event_id=%s message_id=%s",
            queued_event.event_id,
            queued_event.message_id,
        )

        try:
            completed = await self.worker.process_reserved_async(queued_event)
        except Exception:
            logger.exception(
                "Unhandled worker failure event_id=%s",
                queued_event.event_id,
            )
            return False

        if completed:
            acknowledged = self.queue.acknowledge(queued_event.message_id)
            logger.info(
                "Event processed event_id=%s acknowledged=%s",
                queued_event.event_id,
                acknowledged,
            )

        return completed

    async def run(self) -> None:
        logger.info("Worker runner started")
        while not self._stop_event.is_set():
            processed = await self.run_once()
            if not processed:
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.poll_interval,
                    )
                except asyncio.TimeoutError:
                    pass
        logger.info("Worker runner stopped")

if __name__ == "__main__":
    asyncio.run(WorkerRunner().run())
