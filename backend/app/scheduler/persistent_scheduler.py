import asyncio
import datetime
import logging
from sqlalchemy import select, update
from backend.app.database import AsyncSessionLocal
from backend.app.models import Job, Execution, ExecutionLog, utcnow
from backend.app.scheduler.cron_utils import calculate_next_run
from backend.app.workers.job_manager import job_manager

logger = logging.getLogger("telegram_cloner.scheduler")


class PersistentScheduler:
    """
    Authoritative database-backed persistent scheduler.
    Runs inside the container without relying on host-level cron.
    """

    def __init__(self, check_interval_seconds: float = 10.0):
        self.check_interval = check_interval_seconds
        self._running = False
        self._task: asyncio.Task = None

    async def start(self):
        """Start the scheduler background loop and run startup recovery."""
        self._running = True
        logger.info("Starting PersistentScheduler...")
        await self.recover_on_startup()
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop the scheduler loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PersistentScheduler stopped.")

    async def recover_on_startup(self):
        """
        Run upon application startup / Docker container restart:
        1. Clean up jobs that were left in RUNNING state when container was restarted.
        2. Inspect missed schedules and execute or skip according to if_missed policy.
        """
        logger.info("Performing startup scheduler recovery...")
        now = utcnow()

        try:
            async with AsyncSessionLocal() as session:
                # 1. Clean up stale running jobs
                stale_jobs_stmt = select(Job).where(Job.status == "RUNNING")
                res = await session.execute(stale_jobs_stmt)
                stale_jobs = res.scalars().all()

                for job in stale_jobs:
                    logger.warning(
                        f"Job {job.id} ('{job.name}') was marked RUNNING during restart. Cleaning up..."
                    )
                    # Mark any active executions as STOPPED
                    exec_stmt = (
                        select(Execution)
                        .where(Execution.job_id == job.id, Execution.status == "RUNNING")
                    )
                    exec_res = await session.execute(exec_stmt)
                    for execution in exec_res.scalars().all():
                        execution.status = "STOPPED"
                        execution.finished_at = now
                        execution.error_message = "Execution interrupted by container restart / crash"

                    # Reset job status
                    job.status = "SCHEDULED" if job.schedule_enabled else "IDLE"

                # 2. Check missed schedules for all enabled jobs
                sched_stmt = select(Job).where(Job.schedule_enabled == True)
                res = await session.execute(sched_stmt)
                scheduled_jobs = res.scalars().all()

                for job in scheduled_jobs:
                    # If next_run_at is missing, calculate it
                    if not job.next_run_at:
                        job.next_run_at = calculate_next_run(
                            frequency=job.frequency,
                            schedule_time=job.schedule_time,
                            schedule_days=job.schedule_days,
                            schedule_date=job.schedule_date,
                            cron_expression=job.cron_expression,
                            tz_str=job.timezone,
                            base_time_utc=now,
                        )
                        job.status = "SCHEDULED"
                        continue

                    # If next_run_at was in the past (missed while container was offline)
                    if job.next_run_at < now:
                        logger.info(
                            f"Job {job.id} ('{job.name}') missed scheduled run at {job.next_run_at}. Policy: {job.if_missed}"
                        )
                        if job.if_missed == "run_once":
                            # Calculate subsequent future next_run_at first
                            next_future = calculate_next_run(
                                frequency=job.frequency,
                                schedule_time=job.schedule_time,
                                schedule_days=job.schedule_days,
                                schedule_date=job.schedule_date,
                                cron_expression=job.cron_expression,
                                tz_str=job.timezone,
                                base_time_utc=now,
                            )
                            job.next_run_at = next_future
                            job.status = "RUNNING"

                            # Create catch-up execution
                            stmt = select(Execution).where(Execution.job_id == job.id)
                            res_execs = await session.execute(stmt)
                            count = len(res_execs.scalars().all())

                            catch_up_exec = Execution(
                                job_id=job.id,
                                execution_number=count + 1,
                                trigger="SCHEDULED",
                                status="RUNNING",
                                started_at=now,
                            )
                            session.add(catch_up_exec)
                            await session.flush()

                            # Start the job worker in background
                            asyncio.create_task(
                                job_manager.start_job(
                                    job.id, trigger="SCHEDULED", execution_id=catch_up_exec.id
                                )
                            )
                        else:
                            # Policy is 'skip': advance next_run_at to the future
                            logger.info(f"Skipping missed execution for job {job.id} as per policy.")
                            job.next_run_at = calculate_next_run(
                                frequency=job.frequency,
                                schedule_time=job.schedule_time,
                                schedule_days=job.schedule_days,
                                schedule_date=job.schedule_date,
                                cron_expression=job.cron_expression,
                                tz_str=job.timezone,
                                base_time_utc=now,
                            )
                            job.status = "SCHEDULED"

                await session.commit()
                logger.info("Startup scheduler recovery completed.")

        except Exception as exc:
            logger.exception(f"Error during scheduler startup recovery: {exc}")

    async def _scheduler_loop(self):
        """Main periodic loop inspecting database for scheduled jobs."""
        while self._running:
            try:
                await self._check_and_trigger_jobs()
            except Exception as exc:
                logger.exception(f"Exception in scheduler loop: {exc}")

            await asyncio.sleep(self.check_interval)

    async def _check_and_trigger_jobs(self):
        """Query database for jobs whose next_run_at has arrived."""
        now = utcnow()

        async with AsyncSessionLocal() as session:
            stmt = select(Job).where(
                Job.schedule_enabled == True,
                Job.next_run_at != None,
                Job.next_run_at <= now,
            )
            res = await session.execute(stmt)
            due_jobs = res.scalars().all()

            for job in due_jobs:
                is_running = job_manager.is_job_running(job.id)

                # Check overlapping execution setting
                if is_running and job.if_running == "skip":
                    logger.warning(
                        f"Job {job.id} ('{job.name}') is still running. Next scheduled run at {job.next_run_at} SKIPPED per overlap policy."
                    )
                    # Advance next_run_at without triggering
                    job.next_run_at = calculate_next_run(
                        frequency=job.frequency,
                        schedule_time=job.schedule_time,
                        schedule_days=job.schedule_days,
                        schedule_date=job.schedule_date,
                        cron_expression=job.cron_expression,
                        tz_str=job.timezone,
                        base_time_utc=now,
                    )
                    continue

                # Calculate next future run
                next_future = calculate_next_run(
                    frequency=job.frequency,
                    schedule_time=job.schedule_time,
                    schedule_days=job.schedule_days,
                    schedule_date=job.schedule_date,
                    cron_expression=job.cron_expression,
                    tz_str=job.timezone,
                    base_time_utc=now,
                )

                # If frequency is 'once', disable schedule after this run
                if job.frequency == "once":
                    job.schedule_enabled = False
                    job.next_run_at = None
                else:
                    job.next_run_at = next_future

                job.status = "RUNNING"

                # Create execution record
                stmt = select(Execution).where(Execution.job_id == job.id)
                res_execs = await session.execute(stmt)
                count = len(res_execs.scalars().all())

                execution = Execution(
                    job_id=job.id,
                    execution_number=count + 1,
                    trigger="SCHEDULED",
                    status="RUNNING",
                    started_at=now,
                )
                session.add(execution)
                await session.flush()
                execution_id = execution.id

                # Trigger execution via JobManager
                asyncio.create_task(
                    job_manager.start_job(
                        job.id, trigger="SCHEDULED", execution_id=execution_id
                    )
                )

            await session.commit()


persistent_scheduler = PersistentScheduler()
