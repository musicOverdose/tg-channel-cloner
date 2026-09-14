import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


# Auth Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime.datetime


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# Bot Schemas
class BotCreate(BaseModel):
    name: str
    token: str


class BotUpdate(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    is_active: Optional[bool] = None


class BotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bot_username: Optional[str] = None
    telegram_id: Optional[int] = None
    masked_token: str
    is_active: bool
    created_at: datetime.datetime


class BotTestResponse(BaseModel):
    success: bool
    bot_id: Optional[int] = None
    bot_username: Optional[str] = None
    first_name: Optional[str] = None
    error: Optional[str] = None


# Channel Probe Schemas
class ChannelProbeRequest(BaseModel):
    bot_id: int
    chat_id: str


class ChannelProbeResponse(BaseModel):
    success: bool
    chat_id: str
    title: Optional[str] = None
    username: Optional[str] = None
    type: Optional[str] = None
    can_post_messages: bool = False
    is_admin: bool = False
    latest_message_id: Optional[int] = None
    has_protected_content: bool = False
    error: Optional[str] = None


# Job Schemas
class JobCreate(BaseModel):
    name: str
    bot_id: int
    source_chat_id: str
    destination_chat_id: str
    source_title: Optional[str] = None
    destination_title: Optional[str] = None

    copy_mode: str = Field(default="incremental", description="'incremental', 'full', or 'range'")
    start_message_id: int = 1
    end_message_id: Optional[int] = None
    batch_size: int = 50
    delay_between_batches: float = 1.0

    schedule_enabled: bool = False
    frequency: str = Field(default="daily", description="'once', 'daily', 'weekly', 'custom'")
    schedule_time: str = "01:00"
    schedule_days: str = '["mon"]'
    schedule_date: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: str = "UTC"

    if_running: str = Field(default="skip", description="'skip' or 'allow'")
    if_missed: str = Field(default="run_once", description="'run_once' or 'skip'")


class JobUpdate(BaseModel):
    name: Optional[str] = None
    bot_id: Optional[int] = None
    source_chat_id: Optional[str] = None
    destination_chat_id: Optional[str] = None
    source_title: Optional[str] = None
    destination_title: Optional[str] = None

    copy_mode: Optional[str] = None
    start_message_id: Optional[int] = None
    end_message_id: Optional[int] = None
    last_copied_message_id: Optional[int] = None
    batch_size: Optional[int] = None
    delay_between_batches: Optional[float] = None

    schedule_enabled: Optional[bool] = None
    frequency: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_days: Optional[str] = None
    schedule_date: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None

    if_running: Optional[str] = None
    if_missed: Optional[str] = None
    status: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bot_id: int
    bot_name: Optional[str] = None
    bot_username: Optional[str] = None
    source_chat_id: str
    destination_chat_id: str
    source_title: Optional[str] = None
    destination_title: Optional[str] = None

    copy_mode: str
    start_message_id: int
    end_message_id: Optional[int] = None
    last_copied_message_id: int
    batch_size: int
    delay_between_batches: float

    schedule_enabled: bool
    frequency: str
    schedule_time: str
    schedule_days: str
    schedule_date: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: str

    if_running: str
    if_missed: str

    status: str
    next_run_at: Optional[datetime.datetime] = None
    last_run_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    current_execution_id: Optional[int] = None


# Execution Schemas
class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    execution_number: int
    trigger: str
    status: str
    started_at: datetime.datetime
    finished_at: Optional[datetime.datetime] = None
    processed_count: int
    copied_count: int
    skipped_count: int
    error_count: int
    start_msg_id: int
    end_msg_id: int
    current_msg_id: int
    speed: float
    error_message: Optional[str] = None
    created_at: datetime.datetime


class ExecutionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    job_id: int
    timestamp: datetime.datetime
    level: str
    message: str


class JobDetailResponse(JobResponse):
    bot: Optional[BotResponse] = None
    executions: List[ExecutionResponse] = []


# Dashboard & Upcoming Runs Schemas
class UpcomingRunResponse(BaseModel):
    job_id: int
    job_name: str
    bot_username: Optional[str] = None
    source_title: Optional[str] = None
    destination_title: Optional[str] = None
    next_run_at: datetime.datetime
    frequency: str
    timezone: str


class DashboardStats(BaseModel):
    total_jobs: int
    running_jobs: int
    scheduled_jobs: int
    total_copied_messages: int
    upcoming_runs: List[UpcomingRunResponse] = []


class SystemInfoResponse(BaseModel):
    version: str = "1.0.0"
    status: str = "healthy"
    database_type: str
    max_concurrent_jobs: int
    active_workers: int
    system_time_utc: datetime.datetime
