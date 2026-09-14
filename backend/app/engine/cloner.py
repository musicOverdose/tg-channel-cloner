import asyncio
import datetime
import logging
import time
from typing import Optional, Callable, Awaitable
from sqlalchemy import select, update
from backend.app.database import AsyncSessionLocal
from backend.app.models import Job, Bot, Execution, ExecutionLog, utcnow
from backend.app.security import decrypt_token
from backend.app.engine.telegram_client import TelegramClient, TelegramError

logger = logging.getLogger("telegram_cloner.cloner")

MAX_CONSECUTIVE_MISSING_GAP = 50  # Number of consecutive missing messages to consider end-of-channel reached


class ChannelCloner:
    """Core cloning engine for copying Telegram channel messages."""

    def __init__(
        self,
        job_id: int,
        execution_id: int,
        stop_event: asyncio.Event,
        on_progress: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.job_id = job_id
        self.execution_id = execution_id
        self.stop_event = stop_event
        self.on_progress = on_progress

    async def log(self, level: str, message: str):
        """Append an execution log entry to the database and stdout."""
        logger.info(f"[Job {self.job_id} - Exec {self.execution_id}] [{level}] {message}")
        try:
            async with AsyncSessionLocal() as session:
                log_entry = ExecutionLog(
                    execution_id=self.execution_id,
                    job_id=self.job_id,
                    timestamp=utcnow(),
                    level=level,
                    message=message,
                )
                session.add(log_entry)
                await session.commit()
        except Exception as exc:
            logger.error(f"Failed to persist execution log: {exc}")

    async def run(self):
        """Execute the cloning job."""
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, self.job_id)
            if not job:
                logger.error(f"Job {self.job_id} not found")
                return

            bot = await session.get(Bot, job.bot_id)
            if not bot:
                await self.log("ERROR", f"Bot {job.bot_id} not found for job {self.job_id}")
                await self._fail_execution("Bot not found")
                return

            token = decrypt_token(bot.token_encrypted)
            client = TelegramClient(bot.id, token)

            # Determine start and end message IDs based on copy_mode
            start_id = 1
            end_id = job.end_message_id

            if job.copy_mode == "incremental":
                start_id = (job.last_copied_message_id or 0) + 1
            elif job.copy_mode == "full":
                start_id = job.start_message_id or 1
            elif job.copy_mode == "range":
                start_id = job.start_message_id or 1
                end_id = job.end_message_id

        await self.log(
            "INFO",
            f"Starting clone job '{job.name}' (Mode: {job.copy_mode}, Start ID: {start_id}, Target: {job.source_chat_id} -> {job.destination_chat_id})",
        )

        # Validate Bot permissions in Destination channel first
        try:
            me = await client.get_me()
            bot_user_id = me.get("id")
            member = await client.get_chat_member(job.destination_chat_id, bot_user_id)
            status = member.get("status")
            can_post = member.get("can_post_messages", False) or status == "creator"
            if not can_post:
                await self.log(
                    "ERROR",
                    f"Bot @{me.get('username')} lacks 'can_post_messages' permission in destination channel {job.destination_chat_id}. Status: {status}",
                )
                await self._fail_execution("Bot cannot post messages to destination channel")
                return
        except TelegramError as te:
            await self.log("WARN", f"Destination chat check returned: {te}. Proceeding with copy attempt...")
        except Exception as exc:
            await self.log("WARN", f"Could not verify destination permissions: {exc}. Proceeding...")

        current_id = start_id
        processed_count = 0
        copied_count = 0
        skipped_count = 0
        error_count = 0
        consecutive_missing = 0
        batch_size = max(1, min(job.batch_size or 50, 100))
        delay = max(0.1, job.delay_between_batches or 1.0)
        start_time = time.time()
        last_progress_time = start_time

        try:
            while True:
                # Check for stop / pause signal
                if self.stop_event.is_set():
                    await self.log("WARN", f"Clone job stopped by user at message ID {current_id}")
                    await self._update_execution_status(
                        "STOPPED",
                        processed_count,
                        copied_count,
                        skipped_count,
                        error_count,
                        start_id,
                        current_id,
                    )
                    return

                # Check if we reached the explicit end_id
                if end_id and current_id > end_id:
                    await self.log("INFO", f"Reached configured end message ID: {end_id}")
                    break

                # Prepare batch of message IDs
                if end_id:
                    batch_end = min(current_id + batch_size - 1, end_id)
                else:
                    batch_end = current_id + batch_size - 1

                message_ids = list(range(current_id, batch_end + 1))
                if not message_ids:
                    break

                # Attempt batch copyMessages (Bot API 7.0+)
                batch_success = False
                try:
                    results = await client.copy_messages(
                        job.destination_chat_id,
                        job.source_chat_id,
                        message_ids,
                    )
                    # If copyMessages succeeded, all messages in batch were copied
                    num_copied = len(results) if isinstance(results, list) else len(message_ids)
                    processed_count += len(message_ids)
                    copied_count += num_copied
                    consecutive_missing = 0
                    batch_success = True
                    current_id = message_ids[-1] + 1

                    # Update last_copied_message_id
                    await self._update_last_copied_id(message_ids[-1])

                except TelegramError as te:
                    # If batch copy fails (e.g. contains deleted messages, service messages, or protected content)
                    # Fall back to copying each message in the batch individually
                    logger.debug(f"Batch copyMessages failed ({te}). Falling back to individual copyMessage.")

                if not batch_success:
                    # Individual fallback
                    for msg_id in message_ids:
                        if self.stop_event.is_set():
                            break

                        processed_count += 1
                        current_id = msg_id

                        try:
                            await client.copy_message(
                                job.destination_chat_id,
                                job.source_chat_id,
                                msg_id,
                            )
                            copied_count += 1
                            consecutive_missing = 0
                            await self._update_last_copied_id(msg_id)
                        except TelegramError as te:
                            error_text = str(te).lower()
                            if "message to copy not found" in error_text or "message can't be copied" in error_text or "message_id_invalid" in error_text:
                                skipped_count += 1
                                consecutive_missing += 1
                            elif "chat_forwards_restricted" in error_text or "can't be forwarded" in error_text:
                                error_count += 1
                                await self.log(
                                    "ERROR",
                                    f"Cannot copy message {msg_id}: Source channel has content protection enabled (has_protected_content).",
                                )
                            else:
                                error_count += 1
                                await self.log("WARN", f"Failed to copy message {msg_id}: {te}")
                        except Exception as exc:
                            error_count += 1
                            await self.log("ERROR", f"Unexpected error copying message {msg_id}: {exc}")

                        # Check if we hit consecutive missing messages gap (end of channel)
                        if not end_id and consecutive_missing >= MAX_CONSECUTIVE_MISSING_GAP:
                            await self.log(
                                "INFO",
                                f"Reached end of channel (detected {consecutive_missing} consecutive missing messages after ID {msg_id - consecutive_missing}).",
                            )
                            break

                    current_id = message_ids[-1] + 1

                # Check if end of channel was reached
                if not end_id and consecutive_missing >= MAX_CONSECUTIVE_MISSING_GAP:
                    break

                # Progress reporting & DB update every 3 seconds
                now = time.time()
                elapsed = max(0.1, now - start_time)
                speed = round(processed_count / elapsed, 2)
                if now - last_progress_time >= 3.0:
                    last_progress_time = now
                    await self._update_execution_progress(
                        processed_count, copied_count, skipped_count, error_count, current_id, speed
                    )
                    if self.on_progress:
                        await self.on_progress({
                            "job_id": self.job_id,
                            "execution_id": self.execution_id,
                            "status": "RUNNING",
                            "processed": processed_count,
                            "copied": copied_count,
                            "skipped": skipped_count,
                            "errors": error_count,
                            "current_msg_id": current_id,
                            "speed": speed,
                        })

                # Pacing delay between batches
                await asyncio.sleep(delay)

            # Completed successfully
            elapsed = max(0.1, time.time() - start_time)
            speed = round(processed_count / elapsed, 2)
            await self.log(
                "INFO",
                f"Clone completed successfully! Copied: {copied_count}, Skipped: {skipped_count}, Errors: {error_count}, Elapsed: {elapsed:.1f}s ({speed} msgs/s)",
            )
            await self._update_execution_status(
                "COMPLETED",
                processed_count,
                copied_count,
                skipped_count,
                error_count,
                start_id,
                current_id,
                speed=speed,
            )

        except Exception as exc:
            logger.exception(f"Unhandled error in clone execution: {exc}")
            await self.log("ERROR", f"Execution failed with unexpected error: {exc}")
            await self._fail_execution(str(exc))

    async def _update_last_copied_id(self, msg_id: int):
        """Persist the highest copied message ID to Job record."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == self.job_id)
                    .values(last_copied_message_id=msg_id, updated_at=utcnow())
                )
                await session.commit()
        except Exception as exc:
            logger.warning(f"Failed to update last_copied_message_id: {exc}")

    async def _update_execution_progress(
        self, processed: int, copied: int, skipped: int, errors: int, current_id: int, speed: float
    ):
        """Update live execution statistics in the database."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Execution)
                    .where(Execution.id == self.execution_id)
                    .values(
                        processed_count=processed,
                        copied_count=copied,
                        skipped_count=skipped,
                        error_count=errors,
                        current_msg_id=current_id,
                        speed=speed,
                    )
                )
                await session.commit()
        except Exception as exc:
            logger.warning(f"Failed to update execution progress: {exc}")

    async def _update_execution_status(
        self,
        status: str,
        processed: int,
        copied: int,
        skipped: int,
        errors: int,
        start_id: int,
        current_id: int,
        speed: float = 0.0,
    ):
        """Update execution record upon completion or stop."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Execution)
                    .where(Execution.id == self.execution_id)
                    .values(
                        status=status,
                        finished_at=utcnow(),
                        processed_count=processed,
                        copied_count=copied,
                        skipped_count=skipped,
                        error_count=errors,
                        start_msg_id=start_id,
                        end_msg_id=current_id,
                        current_msg_id=current_id,
                        speed=speed,
                    )
                )
                # If completed or stopped, reset Job status back to SCHEDULED or IDLE
                job = await session.get(Job, self.job_id)
                if job:
                    new_job_status = "SCHEDULED" if job.schedule_enabled else "IDLE"
                    job.status = new_job_status
                    job.last_run_at = utcnow()
                await session.commit()
        except Exception as exc:
            logger.error(f"Failed to finalize execution record: {exc}")

    async def _fail_execution(self, error_message: str):
        """Record execution failure."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Execution)
                    .where(Execution.id == self.execution_id)
                    .values(
                        status="FAILED",
                        finished_at=utcnow(),
                        error_message=error_message,
                    )
                )
                job = await session.get(Job, self.job_id)
                if job:
                    job.status = "ERROR"
                    job.last_run_at = utcnow()
                await session.commit()
        except Exception as exc:
            logger.error(f"Failed to mark execution as failed: {exc}")
