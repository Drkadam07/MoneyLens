import uuid
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class MoneyLensException(Exception):
    """Base domain exception for MoneyLens."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(MoneyLensException):
    def __init__(self, message: str = "Invalid credentials or unauthenticated", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(MoneyLensException):
    def __init__(self, message: str = "You do not have permission to access this resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN_ACCESS",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(MoneyLensException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(MoneyLensException):
    def __init__(self, message: str = "Resource conflict or duplicate operation", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class StatementValidationError(MoneyLensException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="STATEMENT_VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class UnsupportedStatementFormatError(MoneyLensException):
    def __init__(self, message: str = "This statement format is not supported", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="STATEMENT_FORMAT_UNSUPPORTED",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class FileTooLargeError(MoneyLensException):
    def __init__(self, message: str = "Uploaded file exceeds maximum allowable size", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
        )


async def moneylens_exception_handler(request: Request, exc: MoneyLensException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": {"error_type": type(exc).__name__, "description": str(exc)},
                "request_id": request_id,
            }
        },
    )