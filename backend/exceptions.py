from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class BaseHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "details": details or {}},
        )


class UserAlreadyExistsException(BaseHTTPException):
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="USER_ALREADY_EXISTS",
            message="UserID already exists.",
            details={"user_id": user_id},
        )


class UserNotFoundException(BaseHTTPException):
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message="UserID not found.",
            details={"user_id": user_id},
        )


class InvalidPasswordException(BaseHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_PASSWORD",
            message="Invalid password.",
        )


class InvalidTokenException(BaseHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN",
            message="Invalid authentication token.",
        )


class SubjectNotFoundException(BaseHTTPException):
    def __init__(self, subject_name: str, subject_publish: str, subject_workbook: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SUBJECT_NOT_FOUND",
            message="Subject not found.",
            details={
                "subject_name": subject_name,
                "subject_publish": subject_publish,
                "subject_workbook": subject_workbook,
            },
        )


class MissingRequiredFieldException(BaseHTTPException):
    def __init__(self, fields: list[str]):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_REQUIRED_FIELD",
            message=f"Missing required fields: {', '.join(fields)}",
            details={"fields": fields},
        )


class InvalidDataException(BaseHTTPException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_DATA",
            message=message,
            details=details or {},
        )


class DatabaseConnectionException(BaseHTTPException):
    def __init__(self, error_message: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_CONNECTION_ERROR",
            message="Database connection error.",
            details={"error": error_message},
        )


class FileNotFoundException(BaseHTTPException):
    def __init__(self, file_path: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message="File not found.",
            details={"file_path": file_path},
        )


class UploadFailedException(BaseHTTPException):
    def __init__(self, filename: str, error_message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="UPLOAD_FAILED",
            message="File upload failed.",
            details={"filename": filename, "error": error_message},
        )


class ValidationException(BaseHTTPException):
    def __init__(self, field_name: str, validation_message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Validation error.",
            details={"field_name": field_name, "message": validation_message},
        )


class PermissionDeniedException(BaseHTTPException):
    def __init__(self, resource: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="PERMISSION_DENIED",
            message="Permission denied.",
            details={"resource": resource},
        )


class RateLimitExceededException(BaseHTTPException):
    def __init__(self, limit: int, window: str):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded.",
            details={"limit": limit, "window": window},
        )


class InternalServerException(BaseHTTPException):
    def __init__(self, error_message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error.",
            details={"error": error_message},
        )
