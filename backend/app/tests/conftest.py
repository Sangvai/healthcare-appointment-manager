import os
from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core.database import Base  # noqa: E402
from app.models import *  # noqa: E402,F401,F403 - populate metadata
from app.models.enums import UserRole  # noqa: E402
from app.models.schedule import DoctorWorkingHours  # noqa: E402
from app.models.user import Doctor, Patient, User  # noqa: E402
from app.core.security import hash_password  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture()
def doctor_with_hours(db_session):
    user = User(email="doc@test.com", hashed_password=hash_password("x"), role=UserRole.DOCTOR)
    db_session.add(user)
    db_session.flush()
    doctor = Doctor(user_id=user.id, full_name="Dr. Test")
    db_session.add(doctor)
    db_session.flush()
    for day in range(7):
        db_session.add(
            DoctorWorkingHours(doctor_id=doctor.id, day_of_week=day, start_time=time(10, 0), end_time=time(13, 0), slot_duration_minutes=30)
        )
    db_session.commit()
    return doctor


@pytest.fixture()
def patient(db_session):
    user = User(email="pat@test.com", hashed_password=hash_password("x"), role=UserRole.PATIENT)
    db_session.add(user)
    db_session.flush()
    p = Patient(user_id=user.id, full_name="Patient Test")
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture()
def patient2(db_session):
    user = User(email="pat2@test.com", hashed_password=hash_password("x"), role=UserRole.PATIENT)
    db_session.add(user)
    db_session.flush()
    p = Patient(user_id=user.id, full_name="Patient Two")
    db_session.add(p)
    db_session.commit()
    return p
