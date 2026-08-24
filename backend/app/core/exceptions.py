from fastapi import status


class AppException(Exception):
    """Base application exception mapped to a consistent JSON error response."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ValidationAppError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class ConflictError(AppException):
    """Used for slot-taken / double-booking style conflicts -> HTTP 409."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
