"""Seeds an admin, a few doctors with specializations/working hours, one
patient, and a couple of sample appointments so the app is usable right
after `alembic upgrade head`. Run with: python -m app.seed
"""
from datetime import date, datetime, time, timedelta, timezone

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.schedule import DoctorSpecialization, DoctorWorkingHours
from app.models.user import Doctor, Patient, User


def run():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@clinic.com").first():
            print("Seed data already present, skipping.")
            return

        admin = User(email="admin@clinic.com", hashed_password=hash_password("Admin@12345"), role=UserRole.ADMIN)
        db.add(admin)

        doctors_data = [
            {
                "email": "dr.sharma@clinic.com",
                "full_name": "Dr. Anita Sharma",
                "qualification": "MBBS, MD (General Medicine)",
                "experience_years": 12,
                "specializations": ["General Medicine"],
            },
            {
                "email": "dr.khan@clinic.com",
                "full_name": "Dr. Imran Khan",
                "qualification": "MBBS, MS (Orthopedics)",
                "experience_years": 8,
                "specializations": ["Orthopedics"],
            },
            {
                "email": "dr.iyer@clinic.com",
                "full_name": "Dr. Priya Iyer",
                "qualification": "MBBS, DCH (Pediatrics)",
                "experience_years": 6,
                "specializations": ["Pediatrics"],
            },
        ]

        created_doctors = []
        for d in doctors_data:
            user = User(email=d["email"], hashed_password=hash_password("Doctor@12345"), role=UserRole.DOCTOR)
            db.add(user)
            db.flush()
            doctor = Doctor(
                user_id=user.id,
                full_name=d["full_name"],
                qualification=d["qualification"],
                experience_years=d["experience_years"],
            )
            db.add(doctor)
            db.flush()
            for spec in d["specializations"]:
                db.add(DoctorSpecialization(doctor_id=doctor.id, name=spec))
            for day in range(0, 5):  # Monday-Friday
                db.add(
                    DoctorWorkingHours(
                        doctor_id=doctor.id, day_of_week=day, start_time=time(10, 0), end_time=time(13, 0),
                        slot_duration_minutes=30,
                    )
                )
            created_doctors.append(doctor)

        patient_user = User(email="patient@example.com", hashed_password=hash_password("Patient@12345"), role=UserRole.PATIENT)
        db.add(patient_user)
        db.flush()
        patient = Patient(user_id=patient_user.id, full_name="Ravi Kumar")
        db.add(patient)
        db.flush()

        db.commit()

        next_monday = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
        sample_start = datetime.combine(next_monday, time(10, 0), tzinfo=timezone.utc)
        db.add(
            Appointment(
                patient_id=patient.id,
                doctor_id=created_doctors[0].id,
                start_time=sample_start,
                end_time=sample_start + timedelta(minutes=30),
                status=AppointmentStatus.CONFIRMED,
            )
        )
        db.commit()

        print("Seed complete.")
        print("Admin login: admin@clinic.com / Admin@12345")
        print("Doctor logins: dr.sharma@clinic.com / dr.khan@clinic.com / dr.iyer@clinic.com, password Doctor@12345")
        print("Patient login: patient@example.com / Patient@12345")
    finally:
        db.close()


if __name__ == "__main__":
    run()
