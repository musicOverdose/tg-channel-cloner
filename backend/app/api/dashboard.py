from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from backend.app.database import get_db
from backend.app.models import Job, Execution, User
from backend.app.schemas import DashboardStats, UpcomingRunResponse
from backend.app.workers.job_manager import job_manager
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Total jobs
    total_jobs_res = await db.execute(select(func.count(Job.id)))
    total_jobs = total_jobs_res.scalar() or 0

    # Scheduled jobs
    sched_jobs_res = await db.execute(
        select(func.count(Job.id)).where(Job.schedule_enabled == True)
    )
    scheduled_jobs = sched_jobs_res.scalar() or 0

    # Running jobs (from memory JobManager active tasks)
    running_jobs = len([t for t in job_manager.active_tasks.values() if not t.done()])

    # Total copied messages sum
    copied_sum_res = await db.execute(select(func.sum(Execution.copied_count)))
    total_copied = copied_sum_res.scalar() or 0

    # Upcoming runs list
    stmt = (
        select(Job)
        .options(selectinload(Job.bot))
        .where(Job.schedule_enabled == True, Job.next_run_at != None)
        .order_by(Job.next_run_at.asc())
        .limit(10)
    )
    res = await db.execute(stmt)
    upcoming_jobs = res.scalars().all()

    upcoming_runs = [
        UpcomingRunResponse(
            job_id=j.id,
            job_name=j.name,
            bot_username=j.bot.bot_username if j.bot else None,
            source_title=j.source_title or j.source_chat_id,
            destination_title=j.destination_title or j.destination_chat_id,
            next_run_at=j.next_run_at,
            frequency=j.frequency,
            timezone=j.timezone,
        )
        for j in upcoming_jobs
    ]

    return DashboardStats(
        total_jobs=total_jobs,
        running_jobs=running_jobs,
        scheduled_jobs=scheduled_jobs,
        total_copied_messages=total_copied,
        upcoming_runs=upcoming_runs,
    )
