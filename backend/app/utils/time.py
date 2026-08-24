from datetime import datetime, timezone


def ensure_utc(dt: datetime) -> datetime:
    """SQLite (used in the test suite) drops tzinfo on round-trip even for
    DateTime(timezone=True) columns, while Postgres (production) preserves
    it. Comparing a naive value against an aware `datetime.now(timezone.utc)`
    raises TypeError, so any datetime read back from the DB is normalized
    through this before being compared.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
