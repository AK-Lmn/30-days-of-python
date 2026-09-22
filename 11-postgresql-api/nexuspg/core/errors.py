from typing import Any, Optional


class AppError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class EntityNotFoundError(AppError):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' not found",
            code=f"{entity_name.upper()}_NOT_FOUND",
            status_code=404,
            details={"entity": entity_name, "identifier": str(entity_id)},
        )


class EntityAlreadyExistsError(AppError):
    def __init__(self, entity_name: str, field: str, value: Any):
        super().__init__(
            message=f"{entity_name} with {field} '{value}' already exists",
            code=f"{entity_name.upper()}_ALREADY_EXISTS",
            status_code=409,
            details={"entity": entity_name, "field": field, "value": str(value)},
        )


class ValidationError(AppError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class DatabaseConnectionError(AppError):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="DATABASE_CONNECTION_ERROR",
            status_code=503,
        )
