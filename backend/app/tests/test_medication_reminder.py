from datetime import datetime, timezone

from app.utils.medication import compute_reminder_times


def test_once_daily_creates_one_reminder_per_day():
    start = datetime(2027, 1, 1, 7, 0, tzinfo=timezone.utc)
    reminders = compute_reminder_times("Once daily", start, duration_days=3)
    assert len(reminders) == 3


def test_twice_daily_creates_two_reminders_per_day():
    start = datetime(2027, 1, 1, 7, 0, tzinfo=timezone.utc)
    reminders = compute_reminder_times("Twice daily", start, duration_days=5)
    assert len(reminders) == 10


def test_every_n_hours_spaces_reminders_correctly():
    start = datetime(2027, 1, 1, 8, 0, tzinfo=timezone.utc)
    reminders = compute_reminder_times("Every 8 hours", start, duration_days=1)
    assert len(reminders) == 4  # 0h, 8h, 16h, 24h
    assert (reminders[1] - reminders[0]).total_seconds() == 8 * 3600


def test_unrecognised_frequency_falls_back_to_once_daily():
    start = datetime(2027, 1, 1, 7, 0, tzinfo=timezone.utc)
    reminders = compute_reminder_times("As needed", start, duration_days=2)
    assert len(reminders) == 2
