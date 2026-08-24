from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import CalendarEventStatus
from app.models.mixins import TimestampMixin


class CalendarConnection(Base, TimestampMixin):
    """Stores a user's Google OAuth tokens so the backend can create/update
    calendar events on their behalf."""

    __tablename__ = "calendar_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="google", nullable=False)
    access_token: Mapped[str] = mapped_column(String(2000), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(2000))
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_valid: Mapped[bool] = mapped_column(default=True)


class CalendarEvent(Base, TimestampMixin):
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("appointment_id", "user_id", name="uq_appointment_user_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    google_event_id: Mapped[str | None] = mapped_column(String(255))
    calendar_id: Mapped[str | None] = mapped_column(String(255), default="primary")
    status: Mapped[CalendarEventStatus] = mapped_column(
        Enum(CalendarEventStatus, name="calendar_event_status"), default=CalendarEventStatus.PENDING, nullable=False
    )
    sync_error: Mapped[str | None] = mapped_column(String(1000))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
