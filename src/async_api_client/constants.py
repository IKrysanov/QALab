"""
Константы и реестры для HTTP-клиента.

Здесь живут значения, общие для нескольких модулей:
маппинг статусов на модели ошибок, список чувствительных заголовков и т.д.
"""

from http import HTTPStatus
from typing import Type

from pydantic import BaseModel

from .models.base import (
    ErrorResponse,
    ForbiddenError,
    NotFoundError,
    ServerError,
    UnauthorizedError,
    ValidationErrorResponse,
)

SENSITIVE_HEADERS = frozenset({
    "authorization",
    "x-api-key",
    "cookie",
    "cookies",
    "set-cookie",
    "x-auth-token",
    "proxy-authorization",
})

DEFAULT_ERROR_MODELS: dict[int, Type[BaseModel]] = {
    HTTPStatus.BAD_REQUEST: ErrorResponse,
    HTTPStatus.UNAUTHORIZED: UnauthorizedError,
    HTTPStatus.FORBIDDEN: ForbiddenError,
    HTTPStatus.NOT_FOUND: NotFoundError,
    HTTPStatus.CONFLICT: ErrorResponse,
    HTTPStatus.UNPROCESSABLE_CONTENT: ValidationErrorResponse,
    HTTPStatus.INTERNAL_SERVER_ERROR: ServerError,
    HTTPStatus.BAD_GATEWAY: ServerError,
    HTTPStatus.SERVICE_UNAVAILABLE: ServerError,
    HTTPStatus.GATEWAY_TIMEOUT: ServerError,
}
