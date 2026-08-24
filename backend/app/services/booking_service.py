from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.appointment import Appointment, SlotHold
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, AppointmentStatus, SlotHoldStatus
from app.models.schedule import DoctorWorkingHours
from app.models.user import Doctor
from app.services.slot_service import generate_available_slots, is_doctor_on_leave
from app.utils.time import ensure_utc


def expire_stale_holds(db: Session) -> int:
    """Flips ACTIVE holds whose TTL passed to EXPIRED. Safe to call anytime;
    also run periodically by a Celery beat task so slots free up even if
    nobody hits the API in the meantime."""
    now = datetime.now(timezone.utc)
    stale = db.query(SlotHold).filter(SlotHold.status == SlotHoldStatus.ACTIVE, SlotHold.expires_at <= now)
    count = stale.update({SlotHold.status: SlotHoldStatus.EXPIRED}, synchronize_session=False)
    db.commit()
    return count


def create_slot_hold(db: Session, doctor_id: int, patient_id: int, start_time: datetime) -> SlotHold:
    """Step 1 of booking: reserve a slot for SLOT_HOLD_MINUTES while the
    patient fills the symptom form.

    Concurrency guarantee: two requests for the same doctor+start_time can
    both pass the pre-check below in theory, but only one INSERT can succeed
    because of the partial unique index `uq_doctor_active_hold_start_time`
    on (doctor_id, start_time) WHERE status='ACTIVE'. The loser gets an
    IntegrityError, which we translate into a 409 Conflict.
    """
    expire_stale_holds(db)

    doctor = db.get(Doctor, doctor_id)
    if not doctor or not doctor.is_active:
        raise NotFoundError("Doctor not found")

    if start_time <= datetime.now(timezone.utc):
        raise ValidationAppError("Cannot book a slot in the past")

    if is_doctor_on_leave(db, doctor_id, start_time.date()):
        raise ConflictError("Doctor is on leave on the selected date")

    working_hours = (
        db.query(DoctorWorkingHours)
        .filter(DoctorWorkingHours.doctor_id == doctor_id, DoctorWorkingHours.day_of_week == start_time.weekday())
        .first()
    )
    if not working_hours:
        raise ValidationAppError("Doctor does not work on the selected day")
    duration = timedelta(minutes=working_hours.slot_duration_minutes)

    existing_appointment = db.execute(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time == start_time,
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        )
    ).scalar_one_or_none()
    if existing_appointment:
        raise ConflictError("Slot is already booked")

    hold = SlotHold(
        doctor_id=doctor_id,
        patient_id=patient_id,
        start_time=start_time,
        end_time=start_time + duration,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.SLOT_HOLD_MINUTES),
        status=SlotHoldStatus.ACTIVE,
    )
    db.add(hold)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Slot no longer available, please choose another time")
    db.refresh(hold)
    return hold


def confirm_booking(db: Session, hold_id: int, patient_id: int) -> Appointment:
    """Step 2 of booking: called after the symptom form is submitted.
    Locks the hold row (SELECT ... FOR UPDATE) so concurrent confirm
    attempts on the SAME hold serialize, then relies on the appointments
    table's own partial unique index as the final safety net against any
    other race.
    """
    hold = db.execute(
        select(SlotHold).where(SlotHold.id == hold_id).with_for_update()
    ).scalar_one_or_none()

    if not hold:
        raise NotFoundError("Slot hold not found")
    if hold.patient_id != patient_id:
        raise ConflictError("This slot hold does not belong to you")
    if hold.status != SlotHoldStatus.ACTIVE:
        raise ConflictError("This slot hold is no longer active, please select a slot again")
    if ensure_utc(hold.expires_at) <= datetime.now(timezone.utc):
        hold.status = SlotHoldStatus.EXPIRED
        db.commit()
        raise ConflictError("Slot hold expired, please select a slot again")

    appointment = Appointment(
        patient_id=hold.patient_id,
        doctor_id=hold.doctor_id,
        start_time=hold.start_time,
        end_time=hold.end_time,
        status=AppointmentStatus.CONFIRMED,
    )
    db.add(appointment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Slot no longer available, please choose another time")

    hold.status = SlotHoldStatus.CONVERTED
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(db: Session, appointment: Appointment, reason: str | None = None) -> Appointment:
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_reason = reason
    db.commit()
    db.refresh(appointment)
    return appointment


def reschedule_appointment(db: Session, appointment: Appointment, new_start_time: datetime) -> Appointment:
    """Marks the old appointment RESCHEDULED (freeing its slot via the
    partial unique index) and creates a fresh CONFIRMED appointment at the
    new time. Relies on the same unique index to reject a new_start_time
    that collides with another booking.
    """
    if new_start_time <= datetime.now(timezone.utc):
        raise ValidationAppError("Cannot reschedule to a time in the past")
    if is_doctor_on_leave(db, appointment.doctor_id, new_start_time.date()):
        raise ConflictError("Doctor is on leave on the selected date")

    duration = appointment.end_time - appointment.start_time
    new_appointment = Appointment(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        start_time=new_start_time,
        end_time=new_start_time + duration,
        status=AppointmentStatus.CONFIRMED,
        rescheduled_from_id=appointment.id,
    )
    appointment.status = AppointmentStatus.RESCHEDULED
    db.add(new_appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Selected slot is no longer available")
    db.refresh(new_appointment)
    return new_appointment
