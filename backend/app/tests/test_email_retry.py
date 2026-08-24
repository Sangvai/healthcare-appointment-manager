from unittest.mock import patch

from app.core.config import settings
from app.models.enums import NotificationStatus, NotificationType
from app.services import email_service


def test_failed_email_is_logged_and_marked_retrying(db_session):
    with patch.object(email_service, "_send_via_sendgrid", side_effect=RuntimeError("SendGrid down")):
        log = email_service.send_notification_email(
            db_session,
            "patient@example.com",
            NotificationType.BOOKING_CONFIRMATION,
            {
                "recipient_name": "Test Patient",
                "doctor_name": "Dr. Test",
                "specialization": "General",
                "appointment_time": "01 Jan 2027, 10:00 AM UTC",
            },
        )
    assert log.status == NotificationStatus.RETRYING
    assert log.attempt_count == 1
    assert "SendGrid down" in log.last_error


def test_email_marked_permanently_failed_after_max_attempts(db_session):
    with patch.object(email_service, "_send_via_sendgrid", side_effect=RuntimeError("still down")):
        log = email_service.send_notification_email(
            db_session,
            "patient@example.com",
            NotificationType.CANCELLATION,
            {"recipient_name": "Test", "doctor_name": "Dr. Test", "appointment_time": "x", "reason": "test"},
        )
        for _ in range(settings.MAX_EMAIL_RETRY_ATTEMPTS - 1):
            email_service.retry_email(db_session, log)

    assert log.attempt_count == settings.MAX_EMAIL_RETRY_ATTEMPTS
    assert log.status == NotificationStatus.FAILED


def test_successful_send_marks_status_sent(db_session):
    with patch.object(email_service, "_send_via_sendgrid", return_value=None):
        log = email_service.send_notification_email(
            db_session,
            "patient@example.com",
            NotificationType.BOOKING_CONFIRMATION,
            {
                "recipient_name": "Test Patient",
                "doctor_name": "Dr. Test",
                "specialization": "General",
                "appointment_time": "01 Jan 2027, 10:00 AM UTC",
            },
        )
    assert log.status == NotificationStatus.SENT
    assert log.sent_at is not None
