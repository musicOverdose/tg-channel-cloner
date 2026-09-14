import datetime
import json
import logging
from typing import Optional, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from croniter import croniter

logger = logging.getLogger("telegram_cloner.scheduler.cron_utils")

DAY_MAP = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}


def get_zone_info(tz_str: str) -> ZoneInfo:
    """Safely obtain a ZoneInfo object, falling back to UTC if invalid."""
    try:
        return ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, ValueError, Exception):
        logger.warning(f"Invalid timezone '{tz_str}', falling back to UTC")
        return ZoneInfo("UTC")


def parse_schedule_days(days_raw: Optional[str]) -> List[int]:
    """Parse JSON list of days or comma-separated string to integer list of weekdays (0=Monday, 6=Sunday)."""
    if not days_raw:
        return [0]  # default Monday
    try:
        data = json.loads(days_raw)
        if isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, int) and 0 <= item <= 6:
                    result.append(item)
                elif isinstance(item, str) and item.lower() in DAY_MAP:
                    result.append(DAY_MAP[item.lower()])
            return result if result else [0]
    except Exception:
        pass

    # Fallback to comma separated
    result = []
    for part in str(days_raw).split(","):
        clean = part.strip().lower()
        if clean in DAY_MAP:
            result.append(DAY_MAP[clean])
    return result if result else [0]


def calculate_next_run(
    frequency: str,
    schedule_time: str,  # "HH:MM"
    schedule_days: Optional[str] = None,  # JSON list e.g. ["mon"]
    schedule_date: Optional[str] = None,  # "YYYY-MM-DD" for "once"
    cron_expression: Optional[str] = None,
    tz_str: str = "UTC",
    base_time_utc: Optional[datetime.datetime] = None,
) -> Optional[datetime.datetime]:
    """
    Calculate the next scheduled execution time in UTC.
    Handles timezone and DST transitions accurately.
    """
    tz = get_zone_info(tz_str)
    if base_time_utc is None:
        base_time_utc = datetime.datetime.now(datetime.timezone.utc)

    # Convert base time to target local timezone
    local_now = base_time_utc.astimezone(tz)

    try:
        time_parts = schedule_time.strip().split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
    except Exception:
        hour, minute = 1, 0

    if frequency == "once":
        if not schedule_date:
            return None
        try:
            date_parts = [int(p) for p in schedule_date.strip().split("-")]
            target_local = datetime.datetime(
                date_parts[0], date_parts[1], date_parts[2], hour, minute, 0, tzinfo=tz
            )
            # If the single scheduled time has already passed, return None
            if target_local <= local_now:
                return None
            return target_local.astimezone(datetime.timezone.utc)
        except Exception as exc:
            logger.error(f"Error parsing 'once' schedule date: {exc}")
            return None

    elif frequency == "daily":
        target_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_local <= local_now:
            # Advance to tomorrow in target timezone
            target_local = (local_now + datetime.timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        return target_local.astimezone(datetime.timezone.utc)

    elif frequency == "weekly":
        weekdays = parse_schedule_days(schedule_days)
        # Find the next matching weekday
        candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Check from today up to 14 days in the future
        for day_offset in range(14):
            day_candidate = candidate + datetime.timedelta(days=day_offset)
            if day_candidate.weekday() in weekdays and day_candidate > local_now:
                return day_candidate.astimezone(datetime.timezone.utc)
        # Fallback 7 days
        return (candidate + datetime.timedelta(days=7)).astimezone(datetime.timezone.utc)

    elif frequency == "custom":
        if not cron_expression:
            return None
        try:
            # croniter takes naive local time and timezone
            local_naive = local_now.replace(tzinfo=None)
            cron = croniter(cron_expression.strip(), local_naive)
            next_naive = cron.get_next(datetime.datetime)
            next_local = next_naive.replace(tzinfo=tz)
            return next_local.astimezone(datetime.timezone.utc)
        except Exception as exc:
            logger.error(f"Failed to evaluate cron expression '{cron_expression}': {exc}")
            return None

    return None
