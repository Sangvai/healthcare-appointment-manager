import enum


class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class AppointmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    NO_SHOW = "NO_SHOW"


# Statuses that occupy a real slot on the calendar (used for conflict checks)
ACTIVE_APPOINTMENT_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


class SlotHoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"


class UrgencyLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AISummaryStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class NotificationType(str, enum.Enum):
    BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    CANCELLATION = "CANCELLATION"
    RESCHEDULE = "RESCHEDULE"
    DOCTOR_LEAVE = "DOCTOR_LEAVE"
    MEDICATION_REMINDER = "MEDICATION_REMINDER"


class CalendarEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class MedicationReminderStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
