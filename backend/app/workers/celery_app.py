from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "healthcare",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_default_retry_delay=60,
)

celery_app.conf.beat_schedule = {
    "expire-stale-slot-holds": {
        "task": "app.workers.tasks.task_expire_stale_holds",
        "schedule": 60.0,
    },
    "retry-failed-emails": {
        "task": "app.workers.tasks.task_retry_failed_emails",
        "schedule": 300.0,
    },
    "retry-failed-calendar-syncs": {
        "task": "app.workers.tasks.task_retry_failed_calendar_syncs",
        "schedule": 300.0,
    },
    "send-due-medication-reminders": {
        "task": "app.workers.tasks.task_send_due_medication_reminders",
        "schedule": 60.0,
    },
    "send-appointment-reminders": {
        "task": "app.workers.tasks.task_send_appointment_reminders",
        "schedule": crontab(minute="0,30"),
    },
    "retry-failed-pre-visit-summaries": {
        "task": "app.workers.tasks.task_retry_failed_pre_visit_summaries",
        "schedule": 600.0,
    },
}
