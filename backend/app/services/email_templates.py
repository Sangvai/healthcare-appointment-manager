from app.models.enums import NotificationType

TEMPLATES = {
    NotificationType.BOOKING_CONFIRMATION: {
        "subject": "Appointment Confirmed - {appointment_time}",
        "body": (
            "<p>Hi {recipient_name},</p>"
            "<p>Your appointment with Dr. {doctor_name} ({specialization}) is confirmed for "
            "<b>{appointment_time}</b>.</p>"
            "<p>Please arrive 10 minutes early.</p>"
        ),
    },
    NotificationType.APPOINTMENT_REMINDER: {
        "subject": "Reminder: Appointment on {appointment_time}",
        "body": (
            "<p>Hi {recipient_name},</p>"
            "<p>This is a reminder for your appointment with Dr. {doctor_name} at "
            "<b>{appointment_time}</b>.</p>"
        ),
    },
    NotificationType.CANCELLATION: {
        "subject": "Appointment Cancelled - {appointment_time}",
        "body": (
            "<p>Hi {recipient_name},</p>"
            "<p>Your appointment with Dr. {doctor_name} on <b>{appointment_time}</b> has been "
            "cancelled. Reason: {reason}</p>"
        ),
    },
    NotificationType.RESCHEDULE: {
        "subject": "Appointment Rescheduled",
        "body": (
            "<p>Hi {recipient_name},</p>"
            "<p>Your appointment with Dr. {doctor_name} has been rescheduled to "
            "<b>{appointment_time}</b>.</p>"
        ),
    },
    NotificationType.DOCTOR_LEAVE: {
        "subject": "Your appointment is affected by a doctor's leave",
        "body": (
            "<p>Hi {recipient_name},</p>"
            "<p>Dr. {doctor_name} will be on leave on <b>{leave_date}</b>, which affects your "
            "appointment scheduled at {appointment_time}. Please rebook at your convenience.</p>"
        ),
    },
    NotificationType.MEDICATION_REMINDER: {
        "subject": "Medication Reminder: {medicine}",
        "body": (
            "<p>Hi {recipient_name},</p>"
            "<p>It's time to take <b>{medicine}</b> ({dose}). Frequency: {frequency}.</p>"
        ),
    },
}


def render_template(notification_type: NotificationType, context: dict) -> tuple[str, str]:
    template = TEMPLATES[notification_type]
    subject = template["subject"].format(**context)
    body = template["body"].format(**context)
    return subject, body
