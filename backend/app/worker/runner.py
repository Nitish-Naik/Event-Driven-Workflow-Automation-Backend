import asyncio
import logging

from app.queue.event_queue import EventQueue
from app.worker.event_worker import EventWorker

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
        queued_event = self.queue.reserve()
        if queued_event is None:
            return False

        try:
            completed = await self.worker.process_reserved_async(queued_event)
        except Exception:
            logger.exception("Unhandled worker failure for event %s", queued_event.event_id)
            return False

        if completed:
            self.queue.acknowledge(queued_event.message_id)
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
