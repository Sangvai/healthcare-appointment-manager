import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import admin, appointments, auth, doctors, google, patients
from app.core.config import settings
from app.core.exceptions import AppException

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Healthcare Appointment & Follow-up Manager API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
def handle_app_exception(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "error_code": exc.error_code, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "details": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    logging.getLogger("app").exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "error_code": "INTERNAL_ERROR", "details": {}},
    )


API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(doctors.router, prefix=API_PREFIX)
app.include_router(appointments.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(google.router, prefix=API_PREFIX)
app.include_router(patients.router, prefix=API_PREFIX)


@app.get("/health")
def health_check():
    return {"status": "ok"}
