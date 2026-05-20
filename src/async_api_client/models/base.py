from typing import Any
from pydantic import BaseModel


# === Стандартные модели ошибок ===

class ErrorResponse(BaseModel):
    """Общий формат ошибки. Подойдёт для 4xx/5xx с единым телом."""
    detail: str


class ValidationErrorItem(BaseModel):
    loc: list[Any]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """422 от FastAPI и подобных."""
    detail: list[ValidationErrorItem]


class UnauthorizedError(ErrorResponse):
    """401."""


class ForbiddenError(ErrorResponse):
    """403."""


class NotFoundError(ErrorResponse):
    """404."""


class ServerError(ErrorResponse):
    """5xx."""
