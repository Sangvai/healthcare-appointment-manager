"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("PATIENT", "DOCTOR", "ADMIN", name="user_role")
    appointment_status = sa.Enum(
        "PENDING", "CONFIRMED", "COMPLETED", "CANCELLED", "RESCHEDULED", "NO_SHOW", name="appointment_status"
    )
    slot_hold_status = sa.Enum("ACTIVE", "EXPIRED", "CONVERTED", "CANCELLED", name="slot_hold_status")
    urgency_level = sa.Enum("Low", "Medium", "High", name="urgency_level")
    ai_summary_status = sa.Enum("SUCCESS", "FAILED", "PENDING", name="ai_summary_status")
    post_visit_ai_status = sa.Enum("SUCCESS", "FAILED", "PENDING", name="post_visit_ai_status")
    notification_type = sa.Enum(
        "BOOKING_CONFIRMATION", "APPOINTMENT_REMINDER", "CANCELLATION", "RESCHEDULE", "DOCTOR_LEAVE",
        "MEDICATION_REMINDER", name="notification_type",
    )
    notification_status = sa.Enum("PENDING", "SENT", "FAILED", "RETRYING", name="notification_status")
    email_notification_type = sa.Enum(
        "BOOKING_CONFIRMATION", "APPOINTMENT_REMINDER", "CANCELLATION", "RESCHEDULE", "DOCTOR_LEAVE",
        "MEDICATION_REMINDER", name="email_notification_type",
    )
    email_status = sa.Enum("PENDING", "SENT", "FAILED", "RETRYING", name="email_status")
    calendar_event_status = sa.Enum("PENDING", "SYNCED", "FAILED", "DELETED", name="calendar_event_status")
    medication_reminder_status = sa.Enum("PENDING", "SENT", "FAILED", name="medication_reminder_status")

    bind = op.get_bind()
    for enum in (
        user_role, appointment_status, slot_hold_status, urgency_level, ai_summary_status, post_visit_ai_status,
        notification_type, notification_status, email_notification_type, email_status, calendar_event_status,
        medication_reminder_status,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("gender", sa.String(20)),
        sa.Column("address", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("qualification", sa.String(255)),
        sa.Column("experience_years", sa.Integer),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "doctor_specializations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doctor_id", sa.Integer, sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("doctor_id", "name", name="uq_doctor_specialization"),
    )
    op.create_index("ix_doctor_specializations_doctor_id", "doctor_specializations", ["doctor_id"])

    op.create_table(
        "doctor_working_hours",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doctor_id", sa.Integer, sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("doctor_id", "day_of_week", name="uq_doctor_day"),
    )
    op.create_index("ix_doctor_working_hours_doctor_id", "doctor_working_hours", ["doctor_id"])

    op.create_table(
        "doctor_leaves",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doctor_id", sa.Integer, sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_date", sa.Date, nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("doctor_id", "leave_date", name="uq_doctor_leave_date"),
    )
    op.create_index("ix_doctor_leaves_doctor_id", "doctor_leaves", ["doctor_id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("patient_id", sa.Integer, sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id", sa.Integer, sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="PENDING"),
        sa.Column("cancelled_reason", sa.String(500)),
        sa.Column("rescheduled_from_id", sa.Integer, sa.ForeignKey("appointments.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    # Critical double-booking guard: only one non-cancelled/non-rescheduled
    # appointment per doctor per start_time can exist, enforced at the DB
    # level so no application race condition can violate it.
    op.execute(
        "CREATE UNIQUE INDEX uq_doctor_active_start_time ON appointments (doctor_id, start_time) "
        "WHERE status NOT IN ('CANCELLED', 'RESCHEDULED')"
    )

    op.create_table(
        "slot_holds",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doctor_id", sa.Integer, sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer, sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", slot_hold_status, nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_slot_holds_doctor_id", "slot_holds", ["doctor_id"])
    op.create_index("ix_slot_holds_patient_id", "slot_holds", ["patient_id"])
    op.create_index("ix_slot_holds_status", "slot_holds", ["status"])
    op.execute(
        "CREATE UNIQUE INDEX uq_doctor_active_hold_start_time ON slot_holds (doctor_id, start_time) "
        "WHERE status = 'ACTIVE'"
    )

    op.create_table(
        "symptom_forms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("chief_complaint", sa.String(500), nullable=False),
        sa.Column("symptoms", sa.Text, nullable=False),
        sa.Column("duration", sa.String(100)),
        sa.Column("severity", sa.String(50)),
        sa.Column("additional_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "pre_visit_summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("urgency_level", urgency_level),
        sa.Column("chief_complaint", sa.String(500)),
        sa.Column("suggested_questions", sa.JSON),
        sa.Column("status", ai_summary_status, nullable=False, server_default="PENDING"),
        sa.Column("raw_error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "consultation_notes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("notes", sa.Text, nullable=False),
        sa.Column("diagnosis", sa.String(500)),
        sa.Column("follow_up_instructions", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prescription_medications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("prescription_id", sa.Integer, sa.ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("medicine_name", sa.String(255), nullable=False),
        sa.Column("dose", sa.String(100), nullable=False),
        sa.Column("frequency", sa.String(100), nullable=False),
        sa.Column("duration_days", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prescription_medications_prescription_id", "prescription_medications", ["prescription_id"])

    op.create_table(
        "post_visit_summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("summary", sa.Text),
        sa.Column("medication_schedule", sa.JSON),
        sa.Column("follow_up_steps", sa.JSON),
        sa.Column("status", post_visit_ai_status, nullable=False, server_default="PENDING"),
        sa.Column("raw_error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE")),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("status", notification_status, nullable=False, server_default="PENDING"),
        sa.Column("payload", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_appointment_id", "notifications", ["appointment_id"])

    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("notification_type", email_notification_type, nullable=False),
        sa.Column("status", email_status, nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("template_context", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_logs_recipient", "email_logs", ["recipient"])
    op.create_index("ix_email_logs_status", "email_logs", ["status"])

    op.create_table(
        "calendar_connections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="google"),
        sa.Column("access_token", sa.String(2000), nullable=False),
        sa.Column("refresh_token", sa.String(2000)),
        sa.Column("token_expiry", sa.DateTime(timezone=True)),
        sa.Column("is_valid", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )
    op.create_index("ix_calendar_connections_user_id", "calendar_connections", ["user_id"])

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer, sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("google_event_id", sa.String(255)),
        sa.Column("calendar_id", sa.String(255), server_default="primary"),
        sa.Column("status", calendar_event_status, nullable=False, server_default="PENDING"),
        sa.Column("sync_error", sa.String(1000)),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("appointment_id", "user_id", name="uq_appointment_user_event"),
    )
    op.create_index("ix_calendar_events_appointment_id", "calendar_events", ["appointment_id"])
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])

    op.create_table(
        "medication_reminders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("prescription_medication_id", sa.Integer, sa.ForeignKey("prescription_medications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer, sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", medication_reminder_status, nullable=False, server_default="PENDING"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_medication_reminders_prescription_medication_id", "medication_reminders", ["prescription_medication_id"])
    op.create_index("ix_medication_reminders_patient_id", "medication_reminders", ["patient_id"])
    op.create_index("ix_medication_reminders_scheduled_time", "medication_reminders", ["scheduled_time"])


def downgrade() -> None:
    for table in (
        "medication_reminders", "calendar_events", "calendar_connections", "email_logs", "notifications",
        "post_visit_summaries", "prescription_medications", "prescriptions", "consultation_notes",
        "pre_visit_summaries", "symptom_forms", "slot_holds", "appointments", "doctor_leaves",
        "doctor_working_hours", "doctor_specializations", "doctors", "patients", "users",
    ):
        op.drop_table(table)

    for enum_name in (
        "user_role", "appointment_status", "slot_hold_status", "urgency_level", "ai_summary_status",
        "post_visit_ai_status", "notification_type", "notification_status", "email_notification_type",
        "email_status", "calendar_event_status", "medication_reminder_status",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
