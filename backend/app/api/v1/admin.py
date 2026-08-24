from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.appointment import Appointment
from app.models.enums import NotificationStatus, UserRole
from app.models.notification import EmailLog
from app.models.schedule import DoctorLeave, DoctorSpecialization, DoctorWorkingHours
from app.models.user import Doctor, User
from app.schemas.appointment import AppointmentOut
from app.schemas.doctor import (
    DoctorCreateRequest,
    DoctorLeaveRequest,
    DoctorOut,
    DoctorUpdateRequest,
    LeaveOut,
)
from app.workers.tasks import task_handle_doctor_leave

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/doctors", response_model=DoctorOut, status_code=201)
def create_doctor(payload: DoctorCreateRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise ConflictError("An account with this email already exists")

    user = User(email=payload.email, hashed_password=hash_password(payload.password), role=UserRole.DOCTOR)
    db.add(user)
    db.flush()

    doctor = Doctor(
        user_id=user.id,
        full_name=payload.full_name,
        qualification=payload.qualification,
        experience_years=payload.experience_years,
    )
    db.add(doctor)
    db.flush()

    for name in payload.specializations:
        db.add(DoctorSpecialization(doctor_id=doctor.id, name=name))
    for wh in payload.working_hours:
        db.add(DoctorWorkingHours(doctor_id=doctor.id, **wh.model_dump()))

    if payload.phone:
        user.phone = payload.phone

    db.commit()
    db.refresh(doctor)
    return doctor


@router.patch("/doctors/{doctor_id}", response_model=DoctorOut)
def update_doctor(doctor_id: int, payload: DoctorUpdateRequest, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise NotFoundError("Doctor not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.post("/doctors/{doctor_id}/leave", response_model=LeaveOut, status_code=201)
def add_leave(doctor_id: int, payload: DoctorLeaveRequest, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise NotFoundError("Doctor not found")
    if db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor_id, DoctorLeave.leave_date == payload.leave_date
    ).first():
        raise ConflictError("Leave already recorded for this date")

    leave = DoctorLeave(doctor_id=doctor_id, leave_date=payload.leave_date, reason=payload.reason)
    db.add(leave)
    db.commit()
    db.refresh(leave)

    # Any existing bookings on this date must be resolved (cancel + notify),
    # never silently orphaned. Runs async so this request returns fast.
    task_handle_doctor_leave.delay(doctor_id, payload.leave_date.isoformat())
    return leave


@router.delete("/doctors/{doctor_id}/leave", status_code=204)
def remove_leave(doctor_id: int, leave_date: str, db: Session = Depends(get_db)):
    from datetime import date

    leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor_id, DoctorLeave.leave_date == date.fromisoformat(leave_date)
    ).first()
    if not leave:
        raise NotFoundError("Leave record not found")
    db.delete(leave)
    db.commit()


@router.get("/appointments", response_model=list[AppointmentOut])
def list_all_appointments(db: Session = Depends(get_db)):
    return db.query(Appointment).order_by(Appointment.start_time.desc()).all()


@router.get("/notifications/failures")
def list_notification_failures(db: Session = Depends(get_db)):
    failures = db.query(EmailLog).filter(EmailLog.status == NotificationStatus.FAILED).all()
    return [
        {
            "id": f.id,
            "recipient": f.recipient,
            "notification_type": f.notification_type,
            "attempt_count": f.attempt_count,
            "last_error": f.last_error,
        }
        for f in failures
    ]
