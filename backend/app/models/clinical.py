from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AISummaryStatus, UrgencyLevel
from app.models.mixins import TimestampMixin


class SymptomForm(Base, TimestampMixin):
    __tablename__ = "symptom_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    chief_complaint: Mapped[str] = mapped_column(String(500), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str | None] = mapped_column(String(50))
    additional_notes: Mapped[str | None] = mapped_column(Text)

    appointment: Mapped["Appointment"] = relationship(back_populates="symptom_form")


class PreVisitSummary(Base, TimestampMixin):
    __tablename__ = "pre_visit_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    urgency_level: Mapped[UrgencyLevel | None] = mapped_column(Enum(UrgencyLevel, name="urgency_level"))
    chief_complaint: Mapped[str | None] = mapped_column(String(500))
    suggested_questions: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[AISummaryStatus] = mapped_column(
        Enum(AISummaryStatus, name="ai_summary_status"), default=AISummaryStatus.PENDING, nullable=False
    )
    raw_error: Mapped[str | None] = mapped_column(Text)

    appointment: Mapped["Appointment"] = relationship(back_populates="pre_visit_summary")


class ConsultationNote(Base, TimestampMixin):
    __tablename__ = "consultation_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(String(500))
    follow_up_instructions: Mapped[str | None] = mapped_column(Text)

    appointment: Mapped["Appointment"] = relationship(back_populates="consultation_note")


class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="prescription")
    medications: Mapped[list["PrescriptionMedication"]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan"
    )


class PrescriptionMedication(Base, TimestampMixin):
    __tablename__ = "prescription_medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dose: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)

    prescription: Mapped["Prescription"] = relationship(back_populates="medications")


class PostVisitSummary(Base, TimestampMixin):
    __tablename__ = "post_visit_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    medication_schedule: Mapped[list | None] = mapped_column(JSON)
    follow_up_steps: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[AISummaryStatus] = mapped_column(
        Enum(AISummaryStatus, name="post_visit_ai_status"), default=AISummaryStatus.PENDING, nullable=False
    )
    raw_error: Mapped[str | None] = mapped_column(Text)

    appointment: Mapped["Appointment"] = relationship(back_populates="post_visit_summary")
