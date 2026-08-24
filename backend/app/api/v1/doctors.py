from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_doctor
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.schedule import DoctorSpecialization
from app.models.user import Doctor, User
from app.schemas.appointment import AvailabilityResponse
from app.schemas.doctor import DoctorOut
from app.services.slot_service import generate_available_slots

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/me", response_model=DoctorOut)
def get_my_doctor_profile(db: Session = Depends(get_db), user: User = Depends(require_doctor)):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.specializations), joinedload(Doctor.working_hours))
        .filter(Doctor.user_id == user.id)
        .first()
    )
    if not doctor:
        raise NotFoundError("Doctor profile not found")
    return doctor


@router.get("", response_model=list[DoctorOut])
def list_doctors(specialization: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Doctor).options(
        joinedload(Doctor.specializations), joinedload(Doctor.working_hours)
    ).filter(Doctor.is_active == True)  # noqa: E712
    if specialization:
        query = query.join(DoctorSpecialization).filter(DoctorSpecialization.name.ilike(f"%{specialization}%"))
    return query.all()


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.specializations), joinedload(Doctor.working_hours))
        .filter(Doctor.id == doctor_id)
        .first()
    )
    if not doctor:
        raise NotFoundError("Doctor not found")
    return doctor


@router.get("/{doctor_id}/availability", response_model=AvailabilityResponse)
def get_availability(doctor_id: int, target_date: date = Query(alias="date"), db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise NotFoundError("Doctor not found")
    slots = generate_available_slots(db, doctor_id, target_date)
    return AvailabilityResponse(doctor_id=doctor_id, date=target_date, available_slots=slots)
