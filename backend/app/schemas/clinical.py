from pydantic import BaseModel, Field

from app.models.enums import AISummaryStatus, UrgencyLevel


class PreVisitSummaryOut(BaseModel):
    urgency_level: UrgencyLevel | None
    chief_complaint: str | None
    suggested_questions: list[str] | None
    status: AISummaryStatus
    raw_error: str | None = None

    model_config = {"from_attributes": True}


class PreVisitLLMResult(BaseModel):
    """Strict shape the LLM's JSON output must validate against before we trust it."""

    urgency_level: UrgencyLevel
    chief_complaint: str
    suggested_questions: list[str] = Field(min_length=1, max_length=5)


class MedicationIn(BaseModel):
    medicine_name: str
    dose: str
    frequency: str
    duration_days: int = Field(gt=0)


class ConsultationRequest(BaseModel):
    notes: str
    diagnosis: str | None = None
    follow_up_instructions: str | None = None
    medications: list[MedicationIn] = []


class MedicationScheduleItem(BaseModel):
    medicine: str
    dose: str
    frequency: str
    duration: str


class PostVisitLLMResult(BaseModel):
    summary: str
    medication_schedule: list[MedicationScheduleItem] = []
    follow_up_steps: list[str] = []


class PostVisitSummaryOut(BaseModel):
    summary: str | None
    medication_schedule: list[dict] | None
    follow_up_steps: list[str] | None
    status: AISummaryStatus
    raw_error: str | None = None

    model_config = {"from_attributes": True}
