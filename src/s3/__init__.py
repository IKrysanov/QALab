"""Клиент для объектного хранилища с S3-совместимым API."""

from .client import S3Client
from .config import S3Config
from .exceptions import (
    S3ClientClosedError,
    S3ClientError,
    S3ConfigurationError,
    S3DependencyError,
    S3ObjectTooLargeError,
    S3OperationError,
)
from .models import S3DeleteResult, S3ObjectMetadata, S3UploadResult
from .protocols import S3Service, S3ServiceFactory

__all__ = [
    "S3Client",
    "S3Config",
    "S3ClientClosedError",
    "S3ClientError",
    "S3ConfigurationError",
    "S3DependencyError",
    "S3ObjectTooLargeError",
    "S3OperationError",
    "S3DeleteResult",
    "S3ObjectMetadata",
    "S3Service",
    "S3ServiceFactory",
    "S3UploadResult",
]
