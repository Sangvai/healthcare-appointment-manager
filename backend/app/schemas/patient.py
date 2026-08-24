from datetime import date

from pydantic import BaseModel


class PatientOut(BaseModel):
    id: int
    full_name: str
    date_of_birth: date | None
    gender: str | None
    address: str | None

    model_config = {"from_attributes": True}


class PatientUpdateRequest(BaseModel):
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
