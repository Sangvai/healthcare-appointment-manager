from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import AppointmentStatus, SlotHoldStatus


class AvailabilityResponse(BaseModel):
    doctor_id: int
    date: date
    available_slots: list[datetime]


class SlotHoldRequest(BaseModel):
    doctor_id: int
    start_time: datetime


class SlotHoldResponse(BaseModel):
    id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    expires_at: datetime
    status: SlotHoldStatus

    model_config = {"from_attributes": True}


class BookingConfirmRequest(BaseModel):
    hold_id: int


class SymptomFormRequest(BaseModel):
    chief_complaint: str = Field(min_length=1, max_length=500)
    symptoms: str = Field(min_length=1)
    duration: str | None = None
    severity: str | None = None
    additional_notes: str | None = None


class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    cancelled_reason: str | None

    model_config = {"from_attributes": True}


class RescheduleRequest(BaseModel):
    new_start_time: datetime


class CancelRequest(BaseModel):
    reason: str | None = None
