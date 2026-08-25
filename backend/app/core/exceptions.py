"""
Custom exceptions for domain-level errors, plus the FastAPI handler that
turns them into structured JSON responses.

Why not just `raise HTTPException` everywhere: HTTPException is fine for
simple cases, but defining our own exception types (NotFoundError,
ConflictError, ...) lets the service/repository layers raise meaningful,
framework-agnostic errors without importing FastAPI, and lets us
guarantee every error response has the same shape.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for all domain errors. Not raised directly."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error_code, "message": exc.message}},
    )
