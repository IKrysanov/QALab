"""Pydantic-модели для API."""

from .base import (
    ErrorResponse,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationErrorResponse,
    ServerError,
)

from .posts import Post, PostCreate
# ... и т.д.


__all__ = [
    # Базовые ошибки
    "ErrorResponse",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationErrorResponse",
    "ServerError",

    # Бизнес-модели
    "Post",
    "PostCreate",
]