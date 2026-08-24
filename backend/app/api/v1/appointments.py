from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_doctor, require_patient
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models.appointment import Appointment
from app.models.clinical import ConsultationNote, PostVisitSummary, Prescription, PrescriptionMedication, PreVisitSummary, SymptomForm
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import Doctor, Patient, User
from app.schemas.appointment import (
    AppointmentOut,
    BookingConfirmRequest,
    CancelRequest,
    RescheduleRequest,
    SlotHoldRequest,
    SlotHoldResponse,
    SymptomFormRequest,
)
from app.schemas.clinical import ConsultationRequest, PostVisitSummaryOut, PreVisitSummaryOut
from app.services.booking_service import cancel_appointment, confirm_booking, create_slot_hold, reschedule_appointment
from app.workers.tasks import (
    task_create_medication_reminders,
    task_delete_calendar_events_for_appointment,
    task_generate_post_visit_summary,
    task_generate_pre_visit_summary,
    task_send_booking_confirmation_email,
    task_send_cancellation_email,
    task_send_reschedule_email,
    task_sync_calendar_event,
    task_update_calendar_events_for_appointment,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _patient_of(db: Session, user: User) -> Patient:
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise NotFoundError("Patient profile not found")
    return patient


def _doctor_of(db: Session, user: User) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise NotFoundError("Doctor profile not found")
    return doctor


def _get_appointment_or_404(db: Session, appointment_id: int) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise NotFoundError("Appointment not found")
    return appointment


def _assert_can_view(db: Session, appointment: Appointment, user: User) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.PATIENT:
        patient = _patient_of(db, user)
        if appointment.patient_id != patient.id:
            raise ForbiddenError("Not your appointment")
    elif user.role == UserRole.DOCTOR:
        doctor = _doctor_of(db, user)
        if appointment.doctor_id != doctor.id:
            raise ForbiddenError("Not your appointment")


@router.post("/hold", response_model=SlotHoldResponse, status_code=201)
def hold_slot(payload: SlotHoldRequest, db: Session = Depends(get_db), user: User = Depends(require_patient)):
    patient = _patient_of(db, user)
    hold = create_slot_hold(db, doctor_id=payload.doctor_id, patient_id=patient.id, start_time=payload.start_time)
    return hold


@router.post("", response_model=AppointmentOut, status_code=201)
def book_appointment(
    payload: BookingConfirmRequest, db: Session = Depends(get_db), user: User = Depends(require_patient)
):
    """Converts an active hold into a CONFIRMED appointment. The frontend
    calls POST /appointments/{id}/symptoms right after this to submit the
    symptom form, which in turn triggers AI pre-visit summary generation.
    """
    patient = _patient_of(db, user)
    appointment = confirm_booking(db, hold_id=payload.hold_id, patient_id=patient.id)
    task_send_booking_confirmation_email.delay(appointment.id)
    task_sync_calendar_event.delay(appointment.id, user.id)
    doctor = db.get(Doctor, appointment.doctor_id)
    if doctor:
        doctor_user = db.get(User, doctor.user_id)
        if doctor_user:
            task_sync_calendar_event.delay(appointment.id, doctor_user.id)
    return appointment


@router.get("", response_model=list[AppointmentOut])
def list_appointments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Appointment)
    if user.role == UserRole.PATIENT:
        patient = _patient_of(db, user)
        query = query.filter(Appointment.patient_id == patient.id)
    elif user.role == UserRole.DOCTOR:
        doctor = _doctor_of(db, user)
        query = query.filter(Appointment.doctor_id == doctor.id)
    return query.order_by(Appointment.start_time.desc()).all()


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    return appointment


@router.patch("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(
    appointment_id: int, payload: CancelRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise ValidationAppError("Appointment cannot be cancelled in its current status")
    appointment = cancel_appointment(db, appointment, reason=payload.reason)
    task_send_cancellation_email.delay(appointment.id, reason=payload.reason)
    task_delete_calendar_events_for_appointment.delay(appointment.id)
    return appointment


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(
    appointment_id: int,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
        raise ValidationAppError("Only pending/confirmed appointments can be rescheduled")
    new_appointment = reschedule_appointment(db, appointment, payload.new_start_time)
    task_send_reschedule_email.delay(new_appointment.id)
    task_update_calendar_events_for_appointment.delay(appointment.id)
    return new_appointment


@router.post("/{appointment_id}/symptoms", status_code=201)
def submit_symptoms(
    appointment_id: int,
    payload: SymptomFormRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_patient),
):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    existing = db.query(SymptomForm).filter(SymptomForm.appointment_id == appointment_id).first()
    if existing:
        raise ValidationAppError("Symptoms already submitted for this appointment")

    form = SymptomForm(appointment_id=appointment_id, **payload.model_dump())
    db.add(form)
    db.add(PreVisitSummary(appointment_id=appointment_id))
    db.commit()
    task_generate_pre_visit_summary.delay(appointment_id)
    return {"success": True, "message": "Symptoms submitted, AI summary is being generated"}


@router.get("/{appointment_id}/symptoms")
def get_symptoms(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Raw symptom form, always available regardless of AI summary status -
    the doctor must be able to review the patient's own words even when
    the AI summary failed."""
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    form = db.query(SymptomForm).filter(SymptomForm.appointment_id == appointment_id).first()
    if not form:
        raise NotFoundError("Symptoms not submitted for this appointment yet")
    return {
        "chief_complaint": form.chief_complaint,
        "symptoms": form.symptoms,
        "duration": form.duration,
        "severity": form.severity,
        "additional_notes": form.additional_notes,
    }


@router.get("/{appointment_id}/pre-visit-summary", response_model=PreVisitSummaryOut)
def get_pre_visit_summary(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    summary = db.query(PreVisitSummary).filter(PreVisitSummary.appointment_id == appointment_id).first()
    if not summary:
        raise NotFoundError("Pre-visit summary not available yet")
    return summary


@router.post("/{appointment_id}/consultation", status_code=201)
def submit_consultation(
    appointment_id: int,
    payload: ConsultationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_doctor),
):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)

    note = ConsultationNote(
        appointment_id=appointment_id,
        notes=payload.notes,
        diagnosis=payload.diagnosis,
        follow_up_instructions=payload.follow_up_instructions,
    )
    db.add(note)

    prescription = Prescription(appointment_id=appointment_id)
    db.add(prescription)
    db.flush()
    for med in payload.medications:
        db.add(
            PrescriptionMedication(
                prescription_id=prescription.id,
                medicine_name=med.medicine_name,
                dose=med.dose,
                frequency=med.frequency,
                duration_days=med.duration_days,
            )
        )

    appointment.status = AppointmentStatus.COMPLETED
    db.add(PostVisitSummary(appointment_id=appointment_id))
    db.commit()

    clinical_notes_text = (
        f"Notes: {payload.notes}\nDiagnosis: {payload.diagnosis or 'N/A'}\n"
        f"Follow-up: {payload.follow_up_instructions or 'N/A'}\n"
        + "\n".join(f"Medication: {m.medicine_name} {m.dose} {m.frequency} for {m.duration_days} days" for m in payload.medications)
    )
    task_generate_post_visit_summary.delay(appointment_id, clinical_notes_text)
    if payload.medications:
        task_create_medication_reminders.delay(prescription.id)

    return {"success": True, "message": "Consultation recorded, patient summary is being generated"}


@router.get("/{appointment_id}/post-visit-summary", response_model=PostVisitSummaryOut)
def get_post_visit_summary(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    appointment = _get_appointment_or_404(db, appointment_id)
    _assert_can_view(db, appointment, user)
    summary = db.query(PostVisitSummary).filter(PostVisitSummary.appointment_id == appointment_id).first()
    if not summary:
        raise NotFoundError("Post-visit summary not available yet")
    return summary
