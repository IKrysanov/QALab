"""Pydantic-модели для API.

Общая инфраструктура (ошибки, перечисления) — на верхнем уровне.
Версионные модели лежат в подпакетах:
  • ``models.v1`` — Airflow 2.x (``/api/v1``);
  • ``models.v2`` — Airflow 3.x (``/api/v2``).
"""

from .base import (
    ErrorResponse,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationErrorResponse,
    ServerError,
)
from .common import (
    DagRunState,
    DagRunType,
    DagRunTriggeredByType,
    TaskInstanceState,
    ReprocessBehavior,
    BulkActionOnExistence,
    BulkActionNotOnExistence,
    TimeDelta,
    HTTPExceptionResponse,
)

__all__ = [
    # Базовые ошибки
    "ErrorResponse",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationErrorResponse",
    "ServerError",
    # Common
    "DagRunState", "DagRunType", "DagRunTriggeredByType", "TaskInstanceState",
    "ReprocessBehavior", "BulkActionOnExistence", "BulkActionNotOnExistence",
    "TimeDelta", "HTTPExceptionResponse",
]
