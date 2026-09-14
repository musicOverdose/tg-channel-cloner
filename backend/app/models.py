import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    token_encrypted = Column(Text, nullable=False)
    bot_username = Column(String(128), nullable=True)
    telegram_id = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    jobs = relationship("Job", back_populates="bot", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    source_chat_id = Column(String(64), nullable=False)
    destination_chat_id = Column(String(64), nullable=False)
    source_title = Column(String(255), nullable=True)
    destination_title = Column(String(255), nullable=True)

    # Copying mode
    copy_mode = Column(String(32), default="incremental")  # incremental, full, range
    start_message_id = Column(Integer, default=1)
    end_message_id = Column(Integer, nullable=True)
    last_copied_message_id = Column(Integer, default=0)
    batch_size = Column(Integer, default=50)
    delay_between_batches = Column(Float, default=1.0)

    # Scheduling
    schedule_enabled = Column(Boolean, default=False)
    frequency = Column(String(32), default="daily")  # once, daily, weekly, custom
    schedule_time = Column(String(8), default="01:00")  # "HH:MM"
    schedule_days = Column(String(64), default='["mon"]')  # JSON list e.g. ["mon"]
    schedule_date = Column(String(32), nullable=True)  # YYYY-MM-DD for "once"
    cron_expression = Column(String(64), nullable=True)
    timezone = Column(String(64), default="UTC")

    # Execution policies
    if_running = Column(String(32), default="skip")  # skip, allow
    if_missed = Column(String(32), default="run_once")  # run_once, skip

    # Status & Timestamps
    status = Column(String(32), default="IDLE")  # IDLE, SCHEDULED, RUNNING, PAUSED, ERROR
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    bot = relationship("Bot", back_populates="jobs")
    executions = relationship("Execution", back_populates="job", cascade="all, delete-orphan", order_by="desc(Execution.id)")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    execution_number = Column(Integer, default=1)
    trigger = Column(String(32), default="MANUAL")  # MANUAL, SCHEDULED, RETRY
    status = Column(String(32), default="RUNNING")  # RUNNING, COMPLETED, FAILED, STOPPED, SKIPPED

    started_at = Column(DateTime(timezone=True), default=utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    processed_count = Column(Integer, default=0)
    copied_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    start_msg_id = Column(Integer, default=0)
    end_msg_id = Column(Integer, default=0)
    current_msg_id = Column(Integer, default=0)
    speed = Column(Float, default=0.0)  # msgs/sec
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    job = relationship("Job", back_populates="executions")
    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan", order_by="ExecutionLog.id")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    job_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    level = Column(String(16), default="INFO")
    message = Column(Text, nullable=False)

    execution = relationship("Execution", back_populates="logs")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
