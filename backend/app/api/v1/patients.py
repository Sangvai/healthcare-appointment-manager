from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_patient
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.user import Patient, User
from app.schemas.patient import PatientOut, PatientUpdateRequest

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=PatientOut)
def get_my_profile(db: Session = Depends(get_db), user: User = Depends(require_patient)):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise NotFoundError("Patient profile not found")
    return patient


@router.patch("/me", response_model=PatientOut)
def update_my_profile(
    payload: PatientUpdateRequest, db: Session = Depends(get_db), user: User = Depends(require_patient)
):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise NotFoundError("Patient profile not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient
