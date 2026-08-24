from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class DoctorSpecialization(Base, TimestampMixin):
    __tablename__ = "doctor_specializations"
    __table_args__ = (UniqueConstraint("doctor_id", "name", name="uq_doctor_specialization"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    doctor: Mapped["Doctor"] = relationship(back_populates="specializations")


class DoctorWorkingHours(Base, TimestampMixin):
    """One row per weekday the doctor works. day_of_week: 0=Monday ... 6=Sunday."""

    __tablename__ = "doctor_working_hours"
    __table_args__ = (UniqueConstraint("doctor_id", "day_of_week", name="uq_doctor_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    doctor: Mapped["Doctor"] = relationship(back_populates="working_hours")


class DoctorLeave(Base, TimestampMixin):
    __tablename__ = "doctor_leaves"
    __table_args__ = (UniqueConstraint("doctor_id", "leave_date", name="uq_doctor_leave_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))

    doctor: Mapped["Doctor"] = relationship(back_populates="leaves")
