import asyncio
import logging
from typing import Dict, Optional, Set
from sqlalchemy import select, update
from backend.app.config import settings
from backend.app.database import AsyncSessionLocal
from backend.app.models import Job, Execution, ExecutionLog, utcnow
from backend.app.engine.cloner import ChannelCloner

logger = logging.getLogger("telegram_cloner.workers.job_manager")


class JobManager:
    """Manages worker concurrency, execution dispatching, and cancellation."""

    def __init__(self):
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)
        self.active_tasks: Dict[int, asyncio.Task] = {}  # job_id -> Task
        self.stop_events: Dict[int, asyncio.Event] = {}  # job_id -> Event
        self.active_execution_ids: Dict[int, int] = {}  # job_id -> execution_id
        self._ws_listeners: Set[asyncio.Queue] = set()

    def register_ws_listener(self, queue: asyncio.Queue):
        self._ws_listeners.add(queue)

    def unregister_ws_listener(self, queue: asyncio.Queue):
        self._ws_listeners.discard(queue)

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast a real-time event to all connected WebSocket clients."""
        payload = {"type": event_type, "data": data}
        for q in list(self._ws_listeners):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    def is_job_running(self, job_id: int) -> bool:
        task = self.active_tasks.get(job_id)
        return task is not None and not task.done()

    async def start_job(
        self,
        job_id: int,
        trigger: str = "MANUAL",
        execution_id: Optional[int] = None,
    ) -> Optional[int]:
        """Start a job worker. Returns execution_id if started, None if rejected."""
        if self.is_job_running(job_id):
            logger.warning(f"Job {job_id} is already running!")
            return None

        stop_event = asyncio.Event()
        self.stop_events[job_id] = stop_event

        # Create or update Execution record
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            if not job:
                logger.error(f"Cannot start non-existent job {job_id}")
                return None

            if execution_id is None:
                # Count previous executions for this job
                stmt = select(Execution).where(Execution.job_id == job_id)
                res = await session.execute(stmt)
                count = len(res.scalars().all())

                execution = Execution(
                    job_id=job_id,
                    execution_number=count + 1,
                    trigger=trigger,
                    status="RUNNING",
                    started_at=utcnow(),
                )
                session.add(execution)
                await session.flush()
                execution_id = execution.id

            # Set Job status to RUNNING
            job.status = "RUNNING"
            await session.commit()

        self.active_execution_ids[job_id] = execution_id

        # Launch worker task
        task = asyncio.create_task(
            self._worker_wrapper(job_id, execution_id, stop_event)
        )
        self.active_tasks[job_id] = task

        await self.broadcast("JOB_STARTED", {
            "job_id": job_id,
            "execution_id": execution_id,
            "trigger": trigger,
        })
        return execution_id

    async def _worker_wrapper(self, job_id: int, execution_id: int, stop_event: asyncio.Event):
        """Worker wrapper acquiring semaphore and executing the cloner."""
        async with self.semaphore:
            cloner = ChannelCloner(
                job_id=job_id,
                execution_id=execution_id,
                stop_event=stop_event,
                on_progress=lambda data: self.broadcast("JOB_PROGRESS", data),
            )
            try:
                await cloner.run()
            except Exception as exc:
                logger.exception(f"Exception in cloner for job {job_id}: {exc}")
            finally:
                self.active_tasks.pop(job_id, None)
                self.stop_events.pop(job_id, None)
                self.active_execution_ids.pop(job_id, None)

                # Fetch updated status to broadcast
                async with AsyncSessionLocal() as session:
                    job = await session.get(Job, job_id)
                    exec_rec = await session.get(Execution, execution_id)
                    status = exec_rec.status if exec_rec else "COMPLETED"
                    job_status = job.status if job else "IDLE"

                await self.broadcast("JOB_FINISHED", {
                    "job_id": job_id,
                    "execution_id": execution_id,
                    "status": status,
                    "job_status": job_status,
                })

    async def stop_job(self, job_id: int) -> bool:
        """Signal a running job to stop."""
        event = self.stop_events.get(job_id)
        if event and not event.is_set():
            event.set()
            logger.info(f"Stop signal sent to job {job_id}")
            return True
        return False


job_manager = JobManager()
