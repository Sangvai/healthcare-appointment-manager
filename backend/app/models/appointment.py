from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AppointmentStatus, SlotHoldStatus
from app.models.mixins import TimestampMixin


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"
    __table_args__ = (
        # Hard DB-level guarantee: a doctor can only have ONE non-cancelled
        # appointment starting at a given time, no matter how many requests
        # race for it. Cancelled/rescheduled rows are excluded so the slot
        # can be reused after cancellation.
        Index(
            "uq_doctor_active_start_time",
            "doctor_id",
            "start_time",
            unique=True,
            postgresql_where=(
                'status NOT IN (\'CANCELLED\', \'RESCHEDULED\')'
            ),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"),
        default=AppointmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    cancelled_reason: Mapped[str | None] = mapped_column(String(500))
    rescheduled_from_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))

    patient: Mapped["Patient"] = relationship()
    doctor: Mapped["Doctor"] = relationship()
    symptom_form: Mapped["SymptomForm"] = relationship(back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    pre_visit_summary: Mapped["PreVisitSummary"] = relationship(back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    consultation_note: Mapped["ConsultationNote"] = relationship(back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    prescription: Mapped["Prescription"] = relationship(back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    post_visit_summary: Mapped["PostVisitSummary"] = relationship(back_populates="appointment", uselist=False, cascade="all, delete-orphan")


class SlotHold(Base, TimestampMixin):
    """Short-lived reservation that blocks a slot while a patient fills the
    symptom form, without yet creating a confirmed appointment."""

    __tablename__ = "slot_holds"
    __table_args__ = (
        Index(
            "uq_doctor_active_hold_start_time",
            "doctor_id",
            "start_time",
            unique=True,
            postgresql_where=("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SlotHoldStatus] = mapped_column(
        Enum(SlotHoldStatus, name="slot_hold_status"), default=SlotHoldStatus.ACTIVE, nullable=False, index=True
    )
