import logging
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models.appointment import Appointment
from app.models.calendar import CalendarConnection, CalendarEvent
from app.models.clinical import PreVisitSummary, SymptomForm
from app.models.enums import (
    AISummaryStatus,
    AppointmentStatus,
    CalendarEventStatus,
    MedicationReminderStatus,
    NotificationStatus,
    NotificationType,
)
from app.models.notification import EmailLog, MedicationReminder
from app.models.user import Doctor, Patient, User
from app.services import calendar_service, email_service, llm_service
from app.workers.celery_app import celery_app

logger = logging.getLogger("workers.tasks")


def _appointment_context(db, appointment: Appointment) -> dict:
    patient = db.get(Patient, appointment.patient_id)
    doctor = db.get(Doctor, appointment.doctor_id)
    specialization = doctor.specializations[0].name if doctor and doctor.specializations else "General"
    return {
        "appointment": appointment,
        "patient": patient,
        "doctor": doctor,
        "context": {
            "recipient_name": patient.full_name if patient else "Patient",
            "doctor_name": doctor.full_name if doctor else "Doctor",
            "specialization": specialization,
            "appointment_time": appointment.start_time.strftime("%d %b %Y, %I:%M %p UTC"),
        },
    }


@celery_app.task(name="app.workers.tasks.task_send_booking_confirmation_email")
def task_send_booking_confirmation_email(appointment_id: int):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return
        info = _appointment_context(db, appointment)
        patient_user = db.get(User, info["patient"].user_id) if info["patient"] else None
        doctor_user = db.get(User, info["doctor"].user_id) if info["doctor"] else None
        if patient_user:
            email_service.send_notification_email(
                db, patient_user.email, NotificationType.BOOKING_CONFIRMATION, info["context"]
            )
        if doctor_user:
            email_service.send_notification_email(
                db, doctor_user.email, NotificationType.BOOKING_CONFIRMATION, info["context"]
            )
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_send_cancellation_email")
def task_send_cancellation_email(appointment_id: int, reason: str | None = None):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return
        info = _appointment_context(db, appointment)
        ctx = {**info["context"], "reason": reason or "Not specified"}
        patient_user = db.get(User, info["patient"].user_id) if info["patient"] else None
        doctor_user = db.get(User, info["doctor"].user_id) if info["doctor"] else None
        if patient_user:
            email_service.send_notification_email(db, patient_user.email, NotificationType.CANCELLATION, ctx)
        if doctor_user:
            email_service.send_notification_email(db, doctor_user.email, NotificationType.CANCELLATION, ctx)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_send_reschedule_email")
def task_send_reschedule_email(appointment_id: int):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return
        info = _appointment_context(db, appointment)
        patient_user = db.get(User, info["patient"].user_id) if info["patient"] else None
        doctor_user = db.get(User, info["doctor"].user_id) if info["doctor"] else None
        if patient_user:
            email_service.send_notification_email(db, patient_user.email, NotificationType.RESCHEDULE, info["context"])
        if doctor_user:
            email_service.send_notification_email(db, doctor_user.email, NotificationType.RESCHEDULE, info["context"])
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_sync_calendar_event")
def task_sync_calendar_event(appointment_id: int, user_id: int):
    """Creates (or re-creates) a Google Calendar event for one attendee.
    Best-effort: on any failure the CalendarEvent row is left at FAILED and
    picked up by the periodic retry task; the appointment itself is
    untouched either way.
    """
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)
        conn = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == user_id, CalendarConnection.provider == "google", CalendarConnection.is_valid == True  # noqa: E712
        ).first()
        record = db.query(CalendarEvent).filter(
            CalendarEvent.appointment_id == appointment_id, CalendarEvent.user_id == user_id
        ).first()
        if not record:
            record = CalendarEvent(appointment_id=appointment_id, user_id=user_id, status=CalendarEventStatus.PENDING)
            db.add(record)
            db.flush()

        if not appointment or not conn:
            record.status = CalendarEventStatus.FAILED
            record.sync_error = "No linked Google Calendar connection"
            db.commit()
            return

        info = _appointment_context(db, appointment)
        result = calendar_service.create_event(
            db,
            conn,
            summary=f"Doctor Appointment - Dr. {info['doctor'].full_name if info['doctor'] else ''}",
            description=(
                f"Patient: {info['patient'].full_name if info['patient'] else ''}\n"
                f"Doctor: {info['doctor'].full_name if info['doctor'] else ''}\n"
                f"Specialization: {info['context']['specialization']}\n"
                f"Time: {info['context']['appointment_time']}"
            ),
            start_time=appointment.start_time,
            end_time=appointment.end_time,
        )
        if result.success:
            record.google_event_id = result.event_id
            record.status = CalendarEventStatus.SYNCED
            record.sync_error = None
        else:
            record.status = CalendarEventStatus.FAILED
            record.sync_error = result.error
            record.retry_count += 1
        db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_update_calendar_events_for_appointment")
def task_update_calendar_events_for_appointment(appointment_id: int):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return
        records = db.query(CalendarEvent).filter(
            CalendarEvent.appointment_id == appointment_id, CalendarEvent.status == CalendarEventStatus.SYNCED
        ).all()
        for record in records:
            conn = db.query(CalendarConnection).filter(
                CalendarConnection.user_id == record.user_id, CalendarConnection.provider == "google"
            ).first()
            if not conn or not record.google_event_id:
                continue
            result = calendar_service.update_event(
                db, conn, record.google_event_id, appointment.start_time, appointment.end_time
            )
            if not result.success:
                record.status = CalendarEventStatus.FAILED
                record.sync_error = result.error
                record.retry_count += 1
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_delete_calendar_events_for_appointment")
def task_delete_calendar_events_for_appointment(appointment_id: int):
    db = SessionLocal()
    try:
        records = db.query(CalendarEvent).filter(
            CalendarEvent.appointment_id == appointment_id, CalendarEvent.status == CalendarEventStatus.SYNCED
        ).all()
        for record in records:
            conn = db.query(CalendarConnection).filter(
                CalendarConnection.user_id == record.user_id, CalendarConnection.provider == "google"
            ).first()
            if not conn or not record.google_event_id:
                continue
            result = calendar_service.delete_event(db, conn, record.google_event_id)
            if result.success:
                record.status = CalendarEventStatus.DELETED
                record.sync_error = None
            else:
                record.sync_error = result.error
                record.retry_count += 1
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_retry_failed_calendar_syncs")
def task_retry_failed_calendar_syncs():
    db = SessionLocal()
    try:
        failed = db.query(CalendarEvent).filter(
            CalendarEvent.status == CalendarEventStatus.FAILED, CalendarEvent.retry_count < 5
        ).all()
        for record in failed:
            task_sync_calendar_event.delay(record.appointment_id, record.user_id)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_generate_pre_visit_summary")
def task_generate_pre_visit_summary(appointment_id: int):
    db = SessionLocal()
    try:
        symptom_form = db.query(SymptomForm).filter(SymptomForm.appointment_id == appointment_id).first()
        if not symptom_form:
            return
        summary = db.query(PreVisitSummary).filter(PreVisitSummary.appointment_id == appointment_id).first()
        if not summary:
            summary = PreVisitSummary(appointment_id=appointment_id, status=AISummaryStatus.PENDING)
            db.add(summary)
            db.flush()

        symptoms_text = (
            f"Chief complaint: {symptom_form.chief_complaint}\n"
            f"Symptoms: {symptom_form.symptoms}\n"
            f"Duration: {symptom_form.duration or 'unknown'}\n"
            f"Severity: {symptom_form.severity or 'unknown'}\n"
            f"Additional notes: {symptom_form.additional_notes or 'none'}"
        )
        result = llm_service.generate_pre_visit_summary(symptoms_text)
        if result.success:
            summary.urgency_level = result.data.urgency_level
            summary.chief_complaint = result.data.chief_complaint
            summary.suggested_questions = result.data.suggested_questions
            summary.status = AISummaryStatus.SUCCESS
            summary.raw_error = None
        else:
            summary.status = AISummaryStatus.FAILED
            summary.raw_error = result.error
        db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_retry_failed_pre_visit_summaries")
def task_retry_failed_pre_visit_summaries():
    db = SessionLocal()
    try:
        failed = db.query(PreVisitSummary).filter(PreVisitSummary.status == AISummaryStatus.FAILED).all()
        ids = [s.appointment_id for s in failed]
    finally:
        db.close()
    for appointment_id in ids:
        task_generate_pre_visit_summary.delay(appointment_id)


@celery_app.task(name="app.workers.tasks.task_generate_post_visit_summary")
def task_generate_post_visit_summary(appointment_id: int, clinical_notes: str):
    from app.models.clinical import PostVisitSummary

    db = SessionLocal()
    try:
        summary = db.query(PostVisitSummary).filter(PostVisitSummary.appointment_id == appointment_id).first()
        if not summary:
            summary = PostVisitSummary(appointment_id=appointment_id, status=AISummaryStatus.PENDING)
            db.add(summary)
            db.flush()

        result = llm_service.generate_post_visit_summary(clinical_notes)
        if result.success:
            summary.summary = result.data.summary
            summary.medication_schedule = [m.model_dump() for m in result.data.medication_schedule]
            summary.follow_up_steps = result.data.follow_up_steps
            summary.status = AISummaryStatus.SUCCESS
            summary.raw_error = None
        else:
            summary.status = AISummaryStatus.FAILED
            summary.raw_error = result.error
        db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_create_medication_reminders")
def task_create_medication_reminders(prescription_id: int):
    from app.models.clinical import Prescription
    from app.utils.medication import compute_reminder_times

    db = SessionLocal()
    try:
        prescription = db.get(Prescription, prescription_id)
        if not prescription:
            return
        appointment = db.get(Appointment, prescription.appointment_id)
        start = datetime.now(timezone.utc) + timedelta(hours=1)
        for med in prescription.medications:
            times = compute_reminder_times(med.frequency, start, med.duration_days)
            for t in times:
                db.add(
                    MedicationReminder(
                        prescription_medication_id=med.id,
                        patient_id=appointment.patient_id,
                        scheduled_time=t,
                        status=MedicationReminderStatus.PENDING,
                    )
                )
        db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_send_due_medication_reminders")
def task_send_due_medication_reminders():
    from app.models.clinical import PrescriptionMedication

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = db.query(MedicationReminder).filter(
            MedicationReminder.status == MedicationReminderStatus.PENDING,
            MedicationReminder.scheduled_time <= now,
        ).all()
        for reminder in due:
            med = db.get(PrescriptionMedication, reminder.prescription_medication_id)
            patient = db.get(Patient, reminder.patient_id)
            user = db.get(User, patient.user_id) if patient else None
            if not med or not user:
                reminder.status = MedicationReminderStatus.FAILED
                db.commit()
                continue
            try:
                email_service.send_notification_email(
                    db,
                    user.email,
                    NotificationType.MEDICATION_REMINDER,
                    {
                        "recipient_name": patient.full_name,
                        "medicine": med.medicine_name,
                        "dose": med.dose,
                        "frequency": med.frequency,
                    },
                )
                reminder.status = MedicationReminderStatus.SENT
                reminder.sent_at = now
            except Exception:  # noqa: BLE001
                reminder.status = MedicationReminderStatus.FAILED
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_expire_stale_holds")
def task_expire_stale_holds():
    from app.services.booking_service import expire_stale_holds

    db = SessionLocal()
    try:
        expire_stale_holds(db)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_retry_failed_emails")
def task_retry_failed_emails():
    db = SessionLocal()
    try:
        pending = db.query(EmailLog).filter(
            EmailLog.status.in_([NotificationStatus.FAILED, NotificationStatus.RETRYING])
        ).all()
        for log in pending:
            email_service.retry_email(db, log)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_send_appointment_reminders")
def task_send_appointment_reminders():
    """24h-before reminder. Idempotent via a Notification row keyed on
    (user_id, appointment_id, type) so re-running the beat task never
    double-sends."""
    from app.core.config import settings
    from app.models.notification import Notification

    db = SessionLocal()
    try:
        window_start = datetime.now(timezone.utc) + timedelta(hours=settings.APPOINTMENT_REMINDER_HOURS_BEFORE)
        window_end = window_start + timedelta(minutes=30)
        appointments = db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.CONFIRMED,
            Appointment.start_time >= window_start,
            Appointment.start_time < window_end,
        ).all()
        for appointment in appointments:
            info = _appointment_context(db, appointment)
            for role_user_id in filter(None, [
                info["patient"].user_id if info["patient"] else None,
                info["doctor"].user_id if info["doctor"] else None,
            ]):
                already_sent = db.query(Notification).filter(
                    Notification.user_id == role_user_id,
                    Notification.appointment_id == appointment.id,
                    Notification.type == NotificationType.APPOINTMENT_REMINDER,
                ).first()
                if already_sent:
                    continue
                user = db.get(User, role_user_id)
                email_service.send_notification_email(
                    db, user.email, NotificationType.APPOINTMENT_REMINDER, info["context"]
                )
                db.add(
                    Notification(
                        user_id=role_user_id,
                        appointment_id=appointment.id,
                        type=NotificationType.APPOINTMENT_REMINDER,
                        status=NotificationStatus.SENT,
                    )
                )
                db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.task_handle_doctor_leave")
def task_handle_doctor_leave(doctor_id: int, leave_date_iso: str):
    """Runs when admin marks a doctor on leave for a date with existing
    bookings: cancels the affected appointments, removes their calendar
    events, and notifies both patient and doctor. Nothing is silently
    deleted from the DB - status is set to CANCELLED with a clear reason.
    """
    from datetime import date as date_cls

    leave_date = date_cls.fromisoformat(leave_date_iso)
    db = SessionLocal()
    try:
        day_start = datetime.combine(leave_date, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        affected = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
        ).all()
        affected_ids = [a.id for a in affected]
        for appointment in affected:
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_reason = f"Doctor on leave on {leave_date.isoformat()}"
        db.commit()
    finally:
        db.close()

    for appointment_id in affected_ids:
        task_send_cancellation_email.delay(appointment_id, reason=f"Doctor on leave on {leave_date.isoformat()}")
        task_delete_calendar_events_for_appointment.delay(appointment_id)
