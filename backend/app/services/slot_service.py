from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, SlotHold
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, SlotHoldStatus
from app.models.schedule import DoctorLeave, DoctorWorkingHours
from app.utils.time import ensure_utc


def is_doctor_on_leave(db: Session, doctor_id: int, target_date: date) -> bool:
    return (
        db.query(DoctorLeave)
        .filter(DoctorLeave.doctor_id == doctor_id, DoctorLeave.leave_date == target_date)
        .first()
        is not None
    )


def generate_available_slots(db: Session, doctor_id: int, target_date: date) -> list[datetime]:
    """Builds the list of bookable start times for a doctor on a given date:
    working hours -> minus leave -> minus existing appointments -> minus
    active (non-expired) slot holds.
    """
    if is_doctor_on_leave(db, doctor_id, target_date):
        return []

    day_of_week = target_date.weekday()  # 0=Monday ... 6=Sunday
    working_hours = (
        db.query(DoctorWorkingHours)
        .filter(DoctorWorkingHours.doctor_id == doctor_id, DoctorWorkingHours.day_of_week == day_of_week)
        .first()
    )
    if not working_hours:
        return []

    tz = timezone.utc
    day_start = datetime.combine(target_date, working_hours.start_time, tzinfo=tz)
    day_end = datetime.combine(target_date, working_hours.end_time, tzinfo=tz)
    duration = timedelta(minutes=working_hours.slot_duration_minutes)

    all_slots = []
    cursor = day_start
    while cursor + duration <= day_end:
        all_slots.append(cursor)
        cursor += duration

    now = datetime.now(tz)
    booked_times = {
        ensure_utc(a.start_time)
        for a in db.query(Appointment.start_time).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
        )
    }
    held_times = {
        ensure_utc(h.start_time)
        for h in db.query(SlotHold.start_time).filter(
            SlotHold.doctor_id == doctor_id,
            SlotHold.status == SlotHoldStatus.ACTIVE,
            SlotHold.expires_at > now,
            SlotHold.start_time >= day_start,
            SlotHold.start_time < day_end,
        )
    }

    unavailable = booked_times | held_times
    return [slot for slot in all_slots if slot not in unavailable and slot > now]
