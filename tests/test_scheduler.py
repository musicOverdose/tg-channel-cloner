import pytest
import datetime
from zoneinfo import ZoneInfo
from backend.app.scheduler.cron_utils import calculate_next_run, parse_schedule_days


def test_parse_schedule_days():
    assert parse_schedule_days('["mon", "wed"]') == [0, 2]
    assert parse_schedule_days('["monday", "friday"]') == [0, 4]
    assert parse_schedule_days("mon,fri") == [0, 4]
    assert parse_schedule_days(None) == [0]


def test_daily_schedule_in_tehran_timezone():
    # Fix base time: 2026-09-15 00:00 UTC = 03:30 Asia/Tehran
    # Asia/Tehran is UTC+3:30
    base_utc = datetime.datetime(2026, 9, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)

    # In Tehran, local time is 03:30.
    # Target schedule: Daily at 01:00 Tehran time.
    # Since 03:30 > 01:00, next run should be tomorrow at 01:00 Tehran time.
    # Tomorrow in Tehran is 2026-09-16.
    # 2026-09-16 01:00 Tehran = 2026-09-15 21:30 UTC.
    next_run = calculate_next_run(
        frequency="daily",
        schedule_time="01:00",
        tz_str="Asia/Tehran",
        base_time_utc=base_utc,
    )
    assert next_run is not None
    # Verify in target timezone:
    tehran_time = next_run.astimezone(ZoneInfo("Asia/Tehran"))
    assert tehran_time.hour == 1
    assert tehran_time.minute == 0
    assert tehran_time.day == 16


def test_daily_schedule_before_target_time():
    # Base time: 2026-09-15 00:00 UTC
    # In UTC, local time is 00:00. Target is 01:00 UTC.
    # Since 00:00 < 01:00, next run should be today at 01:00 UTC.
    base_utc = datetime.datetime(2026, 9, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)
    next_run = calculate_next_run(
        frequency="daily",
        schedule_time="01:00",
        tz_str="UTC",
        base_time_utc=base_utc,
    )
    assert next_run is not None
    assert next_run.year == 2026
    assert next_run.month == 9
    assert next_run.day == 15
    assert next_run.hour == 1
    assert next_run.minute == 0


def test_weekly_schedule():
    # 2026-09-14 is a Monday
    base_utc = datetime.datetime(2026, 9, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
    # Schedule every Wednesday at 03:00 UTC
    next_run = calculate_next_run(
        frequency="weekly",
        schedule_time="03:00",
        schedule_days='["wed"]',
        tz_str="UTC",
        base_time_utc=base_utc,
    )
    assert next_run is not None
    assert next_run.weekday() == 2  # Wednesday
    assert next_run.hour == 3
    assert next_run.minute == 0
    assert next_run > base_utc


def test_once_schedule():
    base_utc = datetime.datetime(2026, 9, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
    # Future date
    next_run = calculate_next_run(
        frequency="once",
        schedule_time="15:30",
        schedule_date="2026-09-20",
        tz_str="UTC",
        base_time_utc=base_utc,
    )
    assert next_run is not None
    assert next_run.year == 2026
    assert next_run.month == 9
    assert next_run.day == 20
    assert next_run.hour == 15
    assert next_run.minute == 30

    # Past date returns None
    past_run = calculate_next_run(
        frequency="once",
        schedule_time="10:00",
        schedule_date="2026-09-01",
        tz_str="UTC",
        base_time_utc=base_utc,
    )
    assert past_run is None


def test_custom_cron_schedule():
    # At minute 0 past hour 1 on day-of-month 1
    base_utc = datetime.datetime(2026, 9, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
    next_run = calculate_next_run(
        frequency="custom",
        schedule_time="00:00",
        cron_expression="0 1 * * *",
        tz_str="Europe/Berlin",
        base_time_utc=base_utc,
    )
    assert next_run is not None
    berlin_time = next_run.astimezone(ZoneInfo("Europe/Berlin"))
    assert berlin_time.hour == 1
    assert berlin_time.minute == 0
