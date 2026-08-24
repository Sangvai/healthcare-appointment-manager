from datetime import date, timedelta

from app.services.slot_service import generate_available_slots
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.schedule import DoctorLeave


def _next_weekday(target_weekday: int) -> date:
    today = date.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    return today + timedelta(days=days_ahead or 7)


def test_generates_slots_matching_working_hours_and_duration(db_session, doctor_with_hours):
    target = _next_weekday(0)  # a Monday, which has working hours 10:00-13:00 / 30 min
    slots = generate_available_slots(db_session, doctor_with_hours.id, target)
    assert len(slots) == 6  # 10:00, 10:30, 11:00, 11:30, 12:00, 12:30
    assert slots[0].hour == 10 and slots[0].minute == 0
    assert slots[-1].hour == 12 and slots[-1].minute == 30


def test_no_slots_on_leave_day(db_session, doctor_with_hours):
    target = _next_weekday(0)
    db_session.add(DoctorLeave(doctor_id=doctor_with_hours.id, leave_date=target, reason="Personal"))
    db_session.commit()
    slots = generate_available_slots(db_session, doctor_with_hours.id, target)
    assert slots == []


def test_booked_slot_excluded(db_session, doctor_with_hours, patient):
    target = _next_weekday(0)
    slots_before = generate_available_slots(db_session, doctor_with_hours.id, target)
    taken = slots_before[0]

    db_session.add(
        Appointment(
            patient_id=patient.id,
            doctor_id=doctor_with_hours.id,
            start_time=taken,
            end_time=taken + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
        )
    )
    db_session.commit()

    slots_after = generate_available_slots(db_session, doctor_with_hours.id, target)
    assert taken not in slots_after
    assert len(slots_after) == len(slots_before) - 1
