import logging
from datetime import datetime, timezone

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import NotificationStatus, NotificationType
from app.models.notification import EmailLog
from app.services.email_templates import render_template

logger = logging.getLogger("email_service")


def _send_via_sendgrid(recipient: str, subject: str, html_body: str) -> None:
    if not settings.SENDGRID_API_KEY:
        raise RuntimeError("SendGrid API key is not configured")
    message = Mail(
        from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
        to_emails=recipient,
        subject=subject,
        html_content=html_body,
    )
    client = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = client.send(message)
    if response.status_code >= 300:
        raise RuntimeError(f"SendGrid returned status {response.status_code}")


def send_notification_email(
    db: Session, recipient: str, notification_type: NotificationType, context: dict
) -> EmailLog:
    """Renders the template, attempts delivery, and always persists an
    EmailLog row (sent or failed) so failures are retryable and never
    silently lost. Never raises — a failed send just leaves attempt_count
    at 1 and status=FAILED for the Celery retry task to pick up.
    """
    subject, body = render_template(notification_type, context)
    log = EmailLog(
        recipient=recipient,
        subject=subject,
        notification_type=notification_type,
        status=NotificationStatus.PENDING,
        attempt_count=0,
        template_context=context,
    )
    db.add(log)
    db.flush()

    _attempt_send(db, log, subject, body)
    return log


def _attempt_send(db: Session, log: EmailLog, subject: str, body: str) -> None:
    log.attempt_count += 1
    try:
        _send_via_sendgrid(log.recipient, subject, body)
        log.status = NotificationStatus.SENT
        log.sent_at = datetime.now(timezone.utc)
        log.last_error = None
    except Exception as exc:  # noqa: BLE001 - email failure must never break the caller
        logger.warning("Email send failed for %s (%s): %s", log.recipient, log.notification_type, exc)
        log.last_error = str(exc)
        log.status = (
            NotificationStatus.FAILED
            if log.attempt_count >= settings.MAX_EMAIL_RETRY_ATTEMPTS
            else NotificationStatus.RETRYING
        )
    db.commit()


def retry_email(db: Session, log: EmailLog) -> EmailLog:
    if log.status == NotificationStatus.SENT:
        return log
    if log.attempt_count >= settings.MAX_EMAIL_RETRY_ATTEMPTS:
        log.status = NotificationStatus.FAILED
        db.commit()
        return log
    subject, body = render_template(log.notification_type, log.template_context or {})
    _attempt_send(db, log, subject, body)
    return log
