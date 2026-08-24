from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MedicationReminderStatus, NotificationStatus, NotificationType
from app.models.mixins import TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"), default=NotificationStatus.PENDING, nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSON)


class EmailLog(Base, TimestampMixin):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="email_notification_type"), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="email_status"), default=NotificationStatus.PENDING, nullable=False, index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Context needed to retry/regenerate the email without re-querying the whole domain
    template_context: Mapped[dict | None] = mapped_column(JSON)


class MedicationReminder(Base, TimestampMixin):
    __tablename__ = "medication_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_medication_id: Mapped[int] = mapped_column(
        ForeignKey("prescription_medications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[MedicationReminderStatus] = mapped_column(
        Enum(MedicationReminderStatus, name="medication_reminder_status"),
        default=MedicationReminderStatus.PENDING,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
