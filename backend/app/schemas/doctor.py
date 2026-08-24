from datetime import date, time

from pydantic import BaseModel, EmailStr


class WorkingHoursIn(BaseModel):
    day_of_week: int  # 0=Monday ... 6=Sunday
    start_time: time
    end_time: time
    slot_duration_minutes: int = 30


class DoctorCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    qualification: str | None = None
    experience_years: int | None = None
    specializations: list[str] = []
    working_hours: list[WorkingHoursIn] = []


class DoctorUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    qualification: str | None = None
    experience_years: int | None = None
    is_active: bool | None = None


class SpecializationOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class WorkingHoursOut(BaseModel):
    id: int
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int

    model_config = {"from_attributes": True}


class LeaveOut(BaseModel):
    id: int
    leave_date: date
    reason: str | None

    model_config = {"from_attributes": True}


class DoctorOut(BaseModel):
    id: int
    full_name: str
    qualification: str | None
    experience_years: int | None
    is_active: bool
    specializations: list[SpecializationOut] = []
    working_hours: list[WorkingHoursOut] = []

    model_config = {"from_attributes": True}


class DoctorLeaveRequest(BaseModel):
    leave_date: date
    reason: str | None = None
