"""Конфигурация подключения к AWS S3 или S3-совместимому хранилищу."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Union

from .exceptions import S3ConfigurationError

TLSVerify = Optional[Union[bool, str]]

_ADDRESSING_STYLES = frozenset({"auto", "path", "virtual"})


@dataclass(frozen=True)
class S3Config:
    """Настройки S3, не зависящие от реализации операций с объектами.

    Если явные учётные данные не переданы, boto3 использует стандартную цепочку
    провайдеров: переменные окружения, AWS profile, IAM role и т.д.
    """

    bucket_name: str
    endpoint_url: Optional[str] = None
    region_name: Optional[str] = None
    aws_access_key_id: Optional[str] = field(default=None, repr=False)
    aws_secret_access_key: Optional[str] = field(default=None, repr=False)
    aws_session_token: Optional[str] = field(default=None, repr=False)
    profile_name: Optional[str] = None
    verify_ssl: TLSVerify = None
    addressing_style: str = "auto"
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        normalized_bucket = self.bucket_name.strip()
        if not normalized_bucket:
            raise S3ConfigurationError("bucket_name must not be empty")
        object.__setattr__(self, "bucket_name", normalized_bucket)

        if self.endpoint_url is not None:
            normalized_endpoint = self.endpoint_url.strip().rstrip("/")
            if not normalized_endpoint.startswith(("http://", "https://")):
                raise S3ConfigurationError(
                    "endpoint_url must start with http:// or https://"
                )
            object.__setattr__(self, "endpoint_url", normalized_endpoint)

        for attribute in (
                "aws_access_key_id",
                "aws_secret_access_key",
                "aws_session_token",
        ):
            value = getattr(self, attribute)
            if value is not None and not value.strip():
                raise S3ConfigurationError(f"{attribute} must not be empty")

        has_access_key = self.aws_access_key_id is not None
        has_secret_key = self.aws_secret_access_key is not None
        if has_access_key != has_secret_key:
            raise S3ConfigurationError(
                "aws_access_key_id and aws_secret_access_key must be set together"
            )
        if self.aws_session_token and not (has_access_key and has_secret_key):
            raise S3ConfigurationError(
                "aws_session_token requires aws_access_key_id and aws_secret_access_key"
            )

        normalized_addressing_style = self.addressing_style.lower()
        if normalized_addressing_style not in _ADDRESSING_STYLES:
            raise S3ConfigurationError(
                "addressing_style must be one of: auto, path, virtual"
            )
        object.__setattr__(
            self,
            "addressing_style",
            normalized_addressing_style,
        )

        if not math.isfinite(self.connect_timeout) or self.connect_timeout <= 0:
            raise S3ConfigurationError("connect_timeout must be greater than zero")
        if not math.isfinite(self.read_timeout) or self.read_timeout <= 0:
            raise S3ConfigurationError("read_timeout must be greater than zero")
        if (
                isinstance(self.max_attempts, bool)
                or not isinstance(self.max_attempts, int)
                or self.max_attempts < 1
        ):
            raise S3ConfigurationError("max_attempts must be greater than zero")
