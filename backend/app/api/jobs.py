from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database import get_db
from backend.app.models import Job, Bot, Execution, User, utcnow
from backend.app.schemas import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobDetailResponse,
    ChannelProbeRequest,
    ChannelProbeResponse,
    ExecutionResponse,
)
from backend.app.security import decrypt_token
from backend.app.engine.telegram_client import TelegramClient, TelegramError
from backend.app.scheduler.cron_utils import calculate_next_run
from backend.app.workers.job_manager import job_manager
from backend.app.api.deps import get_current_user
from backend.app.api.bots import format_bot_response

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def format_job_response(job: Job, bot: Optional[Bot] = None) -> JobResponse:
    current_exec_id = job_manager.active_execution_ids.get(job.id)
    # If in memory it's running, ensure status is RUNNING
    display_status = "RUNNING" if job_manager.is_job_running(job.id) else job.status

    bot_name = bot.name if bot else (job.bot.name if job.bot else None)
    bot_username = bot.bot_username if bot else (job.bot.bot_username if job.bot else None)

    return JobResponse(
        id=job.id,
        name=job.name,
        bot_id=job.bot_id,
        bot_name=bot_name,
        bot_username=bot_username,
        source_chat_id=job.source_chat_id,
        destination_chat_id=job.destination_chat_id,
        source_title=job.source_title,
        destination_title=job.destination_title,
        copy_mode=job.copy_mode,
        start_message_id=job.start_message_id,
        end_message_id=job.end_message_id,
        last_copied_message_id=job.last_copied_message_id,
        batch_size=job.batch_size,
        delay_between_batches=job.delay_between_batches,
        schedule_enabled=job.schedule_enabled,
        frequency=job.frequency,
        schedule_time=job.schedule_time,
        schedule_days=job.schedule_days,
        schedule_date=job.schedule_date,
        cron_expression=job.cron_expression,
        timezone=job.timezone,
        if_running=job.if_running,
        if_missed=job.if_missed,
        status=display_status,
        next_run_at=job.next_run_at,
        last_run_at=job.last_run_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        current_execution_id=current_exec_id,
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Job).options(selectinload(Job.bot)).order_by(Job.id.asc())
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [format_job_response(j, j.bot) for j in jobs]


@router.post("", response_model=JobResponse)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Verify bot exists
    bot = await db.get(Bot, payload.bot_id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned Bot not found")

    # Calculate initial next_run_at if schedule is enabled
    next_run = None
    initial_status = "IDLE"
    if payload.schedule_enabled:
        next_run = calculate_next_run(
            frequency=payload.frequency,
            schedule_time=payload.schedule_time,
            schedule_days=payload.schedule_days,
            schedule_date=payload.schedule_date,
            cron_expression=payload.cron_expression,
            tz_str=payload.timezone,
            base_time_utc=utcnow(),
        )
        initial_status = "SCHEDULED"

    new_job = Job(
        name=payload.name.strip(),
        bot_id=payload.bot_id,
        source_chat_id=payload.source_chat_id.strip(),
        destination_chat_id=payload.destination_chat_id.strip(),
        source_title=payload.source_title,
        destination_title=payload.destination_title,
        copy_mode=payload.copy_mode,
        start_message_id=payload.start_message_id,
        end_message_id=payload.end_message_id,
        batch_size=payload.batch_size,
        delay_between_batches=payload.delay_between_batches,
        schedule_enabled=payload.schedule_enabled,
        frequency=payload.frequency,
        schedule_time=payload.schedule_time,
        schedule_days=payload.schedule_days,
        schedule_date=payload.schedule_date,
        cron_expression=payload.cron_expression,
        timezone=payload.timezone,
        if_running=payload.if_running,
        if_missed=payload.if_missed,
        status=initial_status,
        next_run_at=next_run,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    return format_job_response(new_job, bot)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.bot), selectinload(Job.executions))
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    base_resp = format_job_response(job, job.bot)
    bot_resp = format_bot_response(job.bot) if job.bot else None

    # Format executions (take top 25)
    exec_resps = [
        ExecutionResponse(
            id=e.id,
            job_id=e.job_id,
            execution_number=e.execution_number,
            trigger=e.trigger,
            status=e.status,
            started_at=e.started_at,
            finished_at=e.finished_at,
            processed_count=e.processed_count,
            copied_count=e.copied_count,
            skipped_count=e.skipped_count,
            error_count=e.error_count,
            start_msg_id=e.start_msg_id,
            end_msg_id=e.end_msg_id,
            current_msg_id=e.current_msg_id,
            speed=e.speed,
            error_message=e.error_message,
            created_at=e.created_at,
        )
        for e in job.executions[:25]
    ]

    return JobDetailResponse(
        **base_resp.model_dump(),
        bot=bot_resp,
        executions=exec_resps,
    )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    payload: JobUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Update fields
    if payload.name is not None:
        job.name = payload.name.strip()
    if payload.bot_id is not None:
        job.bot_id = payload.bot_id
    if payload.source_chat_id is not None:
        job.source_chat_id = payload.source_chat_id.strip()
    if payload.destination_chat_id is not None:
        job.destination_chat_id = payload.destination_chat_id.strip()
    if payload.source_title is not None:
        job.source_title = payload.source_title
    if payload.destination_title is not None:
        job.destination_title = payload.destination_title
    if payload.copy_mode is not None:
        job.copy_mode = payload.copy_mode
    if payload.start_message_id is not None:
        job.start_message_id = payload.start_message_id
    if payload.end_message_id is not None:
        job.end_message_id = payload.end_message_id
    if payload.last_copied_message_id is not None:
        job.last_copied_message_id = payload.last_copied_message_id
    if payload.batch_size is not None:
        job.batch_size = payload.batch_size
    if payload.delay_between_batches is not None:
        job.delay_between_batches = payload.delay_between_batches
    if payload.if_running is not None:
        job.if_running = payload.if_running
    if payload.if_missed is not None:
        job.if_missed = payload.if_missed

    # Schedule updates
    schedule_changed = False
    if payload.schedule_enabled is not None and payload.schedule_enabled != job.schedule_enabled:
        job.schedule_enabled = payload.schedule_enabled
        schedule_changed = True
    if payload.frequency is not None and payload.frequency != job.frequency:
        job.frequency = payload.frequency
        schedule_changed = True
    if payload.schedule_time is not None and payload.schedule_time != job.schedule_time:
        job.schedule_time = payload.schedule_time
        schedule_changed = True
    if payload.schedule_days is not None and payload.schedule_days != job.schedule_days:
        job.schedule_days = payload.schedule_days
        schedule_changed = True
    if payload.schedule_date is not None:
        job.schedule_date = payload.schedule_date
        schedule_changed = True
    if payload.cron_expression is not None:
        job.cron_expression = payload.cron_expression
        schedule_changed = True
    if payload.timezone is not None and payload.timezone != job.timezone:
        job.timezone = payload.timezone
        schedule_changed = True

    if schedule_changed:
        if job.schedule_enabled:
            job.next_run_at = calculate_next_run(
                frequency=job.frequency,
                schedule_time=job.schedule_time,
                schedule_days=job.schedule_days,
                schedule_date=job.schedule_date,
                cron_expression=job.cron_expression,
                tz_str=job.timezone,
                base_time_utc=utcnow(),
            )
            if not job_manager.is_job_running(job.id):
                job.status = "SCHEDULED"
        else:
            job.next_run_at = None
            if not job_manager.is_job_running(job.id):
                job.status = "PAUSED"

    await db.commit()
    await db.refresh(job)
    bot = await db.get(Bot, job.bot_id)
    return format_job_response(job, bot)


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job_manager.is_job_running(job_id):
        await job_manager.stop_job(job_id)

    await db.delete(job)
    await db.commit()
    return {"status": "success", "message": f"Job {job_id} deleted successfully"}


@router.post("/{job_id}/run")
async def run_job_now(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job_manager.is_job_running(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is already currently executing",
        )

    exec_id = await job_manager.start_job(job_id, trigger="MANUAL")
    if not exec_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to launch job worker",
        )

    return {"status": "success", "message": f"Job {job_id} started", "execution_id": exec_id}


@router.post("/{job_id}/stop")
async def stop_job(
    job_id: int,
    _: User = Depends(get_current_user),
):
    if not job_manager.is_job_running(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not currently running",
        )

    stopped = await job_manager.stop_job(job_id)
    return {"status": "success", "message": "Stop signal sent to job worker"}


@router.post("/{job_id}/pause", response_model=JobResponse)
async def pause_schedule(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.schedule_enabled = False
    job.next_run_at = None
    if not job_manager.is_job_running(job.id):
        job.status = "PAUSED"

    await db.commit()
    await db.refresh(job)
    bot = await db.get(Bot, job.bot_id)
    return format_job_response(job, bot)


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_schedule(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.schedule_enabled = True
    job.next_run_at = calculate_next_run(
        frequency=job.frequency,
        schedule_time=job.schedule_time,
        schedule_days=job.schedule_days,
        schedule_date=job.schedule_date,
        cron_expression=job.cron_expression,
        tz_str=job.timezone,
        base_time_utc=utcnow(),
    )
    if not job_manager.is_job_running(job.id):
        job.status = "SCHEDULED"

    await db.commit()
    await db.refresh(job)
    bot = await db.get(Bot, job.bot_id)
    return format_job_response(job, bot)


@router.post("/probe-channel", response_model=ChannelProbeResponse)
async def probe_channel(
    payload: ChannelProbeRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    bot = await db.get(Bot, payload.bot_id)
    if not bot:
        return ChannelProbeResponse(
            success=False,
            chat_id=payload.chat_id,
            error="Bot not found",
        )

    try:
        raw_token = decrypt_token(bot.token_encrypted)
        client = TelegramClient(bot_id=bot.id, bot_token=raw_token)

        # Get Chat info
        chat_info = await client.get_chat(payload.chat_id)
        chat_title = chat_info.get("title") or chat_info.get("first_name")
        chat_username = chat_info.get("username")
        chat_type = chat_info.get("type")
        has_protected = chat_info.get("has_protected_content", False)

        # Check bot permissions
        me = await client.get_me()
        member_info = await client.get_chat_member(payload.chat_id, me.get("id"))
        status_str = member_info.get("status")
        is_admin = status_str in ("creator", "administrator")
        can_post = member_info.get("can_post_messages", False) or status_str == "creator"

        return ChannelProbeResponse(
            success=True,
            chat_id=payload.chat_id,
            title=chat_title,
            username=chat_username,
            type=chat_type,
            can_post_messages=can_post,
            is_admin=is_admin,
            has_protected_content=has_protected,
        )
    except TelegramError as te:
        return ChannelProbeResponse(
            success=False,
            chat_id=payload.chat_id,
            error=str(te),
        )
    except Exception as exc:
        return ChannelProbeResponse(
            success=False,
            chat_id=payload.chat_id,
            error=f"Unexpected probe error: {exc}",
        )
