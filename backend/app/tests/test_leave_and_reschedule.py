from datetime import date, timedelta

import pytest

from app.core.exceptions import ConflictError
from app.models.schedule import DoctorLeave
from app.services.booking_service import create_slot_hold, reschedule_appointment, confirm_booking
from app.utils.time import ensure_utc


def _next_weekday(target_weekday: int) -> date:
    today = date.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    return today + timedelta(days=days_ahead or 7)


def test_cannot_hold_slot_on_doctor_leave_day(db_session, doctor_with_hours, patient):
    from datetime import datetime, time, timezone

    target = _next_weekday(0)
    db_session.add(DoctorLeave(doctor_id=doctor_with_hours.id, leave_date=target, reason="Conference"))
    db_session.commit()

    slot_time = datetime.combine(target, time(10, 0), tzinfo=timezone.utc)
    with pytest.raises(ConflictError):
        create_slot_hold(db_session, doctor_id=doctor_with_hours.id, patient_id=patient.id, start_time=slot_time)


def test_reschedule_moves_appointment_and_frees_old_slot(db_session, doctor_with_hours, patient):
    from datetime import datetime, time, timezone

    target = _next_weekday(0)
    slot_time = datetime.combine(target, time(10, 0), tzinfo=timezone.utc)
    hold = create_slot_hold(db_session, doctor_id=doctor_with_hours.id, patient_id=patient.id, start_time=slot_time)
    appointment = confirm_booking(db_session, hold_id=hold.id, patient_id=patient.id)

    new_slot_time = datetime.combine(target, time(11, 0), tzinfo=timezone.utc)
    new_appointment = reschedule_appointment(db_session, appointment, new_slot_time)

    assert ensure_utc(new_appointment.start_time) == new_slot_time
    db_session.refresh(appointment)
    assert appointment.status.value == "RESCHEDULED"
