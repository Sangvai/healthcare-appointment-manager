"""The most important test in this suite: proves two patients racing for
the same slot can never both end up with a confirmed appointment, even
when they hit the booking endpoint at effectively the same instant.

Uses a temp-file-backed SQLite DB so each thread gets its OWN connection
(mirroring two separate API processes talking to Postgres) instead of one
shared in-memory connection, which would serialize everything through a
single sqlite3 connection object and not actually exercise the race.
"""
import os
import tempfile
import threading
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models import *  # noqa: F401,F403
from app.models.enums import UserRole
from app.models.schedule import DoctorWorkingHours
from app.models.user import Doctor, Patient, User
from app.services.booking_service import confirm_booking, create_slot_hold
from app.utils.time import ensure_utc


@pytest.fixture()
def shared_engine():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    try:
        os.remove(path)
    except PermissionError:
        pass  # Windows may still hold the file open if a test failed before closing its session


def _seed(engine):
    Session = sessionmaker(bind=engine)
    db = Session()
    doc_user = User(email="doc@race.com", hashed_password=hash_password("x"), role=UserRole.DOCTOR)
    db.add(doc_user)
    db.flush()
    doctor = Doctor(user_id=doc_user.id, full_name="Dr. Race")
    db.add(doctor)
    db.flush()
    db.add(DoctorWorkingHours(doctor_id=doctor.id, day_of_week=0, start_time=time(10, 0), end_time=time(13, 0), slot_duration_minutes=30))

    patients = []
    for i in range(2):
        u = User(email=f"racer{i}@race.com", hashed_password=hash_password("x"), role=UserRole.PATIENT)
        db.add(u)
        db.flush()
        p = Patient(user_id=u.id, full_name=f"Racer {i}")
        db.add(p)
        db.flush()
        patients.append(p)

    db.commit()
    doctor_id, patient_ids = doctor.id, [p.id for p in patients]
    db.close()
    return doctor_id, patient_ids


def _next_monday_10am():
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    target = today + timedelta(days=days_ahead)
    return datetime.combine(target, time(10, 0), tzinfo=timezone.utc)


def test_two_simultaneous_hold_attempts_only_one_wins(shared_engine):
    doctor_id, patient_ids = _seed(shared_engine)
    slot_time = _next_monday_10am()
    Session = sessionmaker(bind=shared_engine)

    results = {}
    barrier = threading.Barrier(2)

    def attempt(idx):
        db = Session()
        try:
            barrier.wait()  # maximize the chance both threads race the same INSERT window
            try:
                hold = create_slot_hold(db, doctor_id=doctor_id, patient_id=patient_ids[idx], start_time=slot_time)
                results[idx] = ("ok", hold.id)
            except ConflictError:
                results[idx] = ("conflict", None)
        finally:
            db.close()

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    outcomes = [results[0][0], results[1][0]]
    assert outcomes.count("ok") == 1, f"Expected exactly one winner, got {results}"
    assert outcomes.count("conflict") == 1, f"Expected exactly one conflict, got {results}"


def test_confirm_booking_after_hold_expired_raises_conflict(shared_engine):
    doctor_id, patient_ids = _seed(shared_engine)
    slot_time = _next_monday_10am()
    Session = sessionmaker(bind=shared_engine)
    db = Session()

    hold = create_slot_hold(db, doctor_id=doctor_id, patient_id=patient_ids[0], start_time=slot_time)
    hold.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    with pytest.raises(ConflictError):
        confirm_booking(db, hold_id=hold.id, patient_id=patient_ids[0])
    db.close()


def test_confirm_booking_succeeds_and_creates_appointment(shared_engine):
    doctor_id, patient_ids = _seed(shared_engine)
    slot_time = _next_monday_10am()
    Session = sessionmaker(bind=shared_engine)
    db = Session()

    hold = create_slot_hold(db, doctor_id=doctor_id, patient_id=patient_ids[0], start_time=slot_time)
    appointment = confirm_booking(db, hold_id=hold.id, patient_id=patient_ids[0])

    assert appointment.doctor_id == doctor_id
    assert ensure_utc(appointment.start_time) == slot_time
    db.close()
