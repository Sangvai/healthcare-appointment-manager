import re
from datetime import datetime, time, timedelta, timezone

FIXED_TIMES_PER_DAY = {
    1: [time(9, 0)],
    2: [time(9, 0), time(21, 0)],
    3: [time(8, 0), time(14, 0), time(20, 0)],
    4: [time(6, 0), time(12, 0), time(18, 0), time(0, 0)],
}

_WORD_TO_COUNT = {
    "once": 1,
    "one time": 1,
    "twice": 2,
    "two times": 2,
    "thrice": 3,
    "three times": 3,
    "four times": 4,
}


def _next_occurrence(base_date, t: time) -> datetime:
    return datetime.combine(base_date, t, tzinfo=timezone.utc)


def compute_reminder_times(frequency: str, start: datetime, duration_days: int) -> list[datetime]:
    """Turns a free-text prescription frequency into a concrete list of
    reminder timestamps for `duration_days` days starting at `start`.

    Supports: "Once/Twice/Three times/Four times daily" and "Every N hours".
    Falls back to once-daily if the phrase isn't recognised, so a reminder
    schedule is always created rather than silently dropped.
    """
    freq = frequency.strip().lower()

    every_match = re.search(r"every\s+(\d+)\s*hours?", freq)
    if every_match:
        interval_hours = int(every_match.group(1))
        total_hours = duration_days * 24
        times = []
        cursor = start
        while (cursor - start).total_seconds() <= total_hours * 3600:
            times.append(cursor)
            cursor += timedelta(hours=interval_hours)
        return times

    count = None
    for phrase, n in _WORD_TO_COUNT.items():
        if phrase in freq:
            count = n
            break
    if count is None:
        digit_match = re.search(r"(\d+)\s*times?", freq)
        count = int(digit_match.group(1)) if digit_match else 1

    daily_times = FIXED_TIMES_PER_DAY.get(count, FIXED_TIMES_PER_DAY[1])
    reminders = []
    for day_offset in range(duration_days):
        day = (start + timedelta(days=day_offset)).date()
        for t in daily_times:
            occurrence = _next_occurrence(day, t)
            if occurrence >= start:
                reminders.append(occurrence)
    return reminders
