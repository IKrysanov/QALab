from .client import AsyncAPIClient
from .config import APIConfig, WebUIConfig, BaseHTTPConfig

from .auth import (
    AsyncAuthStrategy,
    NoAuth,
    BearerAuth,
    APIKeyAuth,
    SessionLoginAuth,
    RefreshableTokenAuth,
)

from .redirects import (
    RedirectChain,
    RedirectHop,
)

from .exceptions import APIError, APITimeoutError

from .models.base import (
    ErrorResponse,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationErrorResponse,
    ServerError,
)

from .http_client import AsyncHTTPClient, HttpxAsyncClient

from .constants import DEFAULT_ERROR_MODELS

__all__ = [
    # Главное
    "AsyncAPIClient",

    # Конфиги
    "APIConfig",
    "WebUIConfig",
    "BaseHTTPConfig",

    # Аутентификация
    "AsyncAuthStrategy",
    "NoAuth",
    "BearerAuth",
    "APIKeyAuth",
    "SessionLoginAuth",
    "RefreshableTokenAuth",

    # Исключения
    "APIError",
    "APITimeoutError",

    # Модели ошибок
    "ErrorResponse",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationErrorResponse",
    "ServerError",

    # Редиректы
    "RedirectChain",
    "RedirectHop",

    # Константы
    "DEFAULT_ERROR_MODELS",

    # Транспорт (продвинутое)
    "AsyncHTTPClient",
    "HttpxAsyncClient",
]


__version__ = "0.1.0"