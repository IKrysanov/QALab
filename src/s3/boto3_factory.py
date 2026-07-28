"""Адаптер создания низкоуровневого boto3 S3 client."""

from __future__ import annotations

from typing import Any

from .config import S3Config
from .exceptions import S3DependencyError
from .protocols import S3Service


class Boto3S3ServiceFactory:
    """Создаёт boto3-клиент, сохраняя импорт SDK на границе приложения."""

    def create(self, config: S3Config) -> S3Service:
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:
            raise S3DependencyError(
                "boto3 is required for S3Client; install project requirements"
            ) from exc

        session_kwargs: dict[str, Any] = {}
        if config.region_name is not None:
            session_kwargs["region_name"] = config.region_name
        if config.aws_access_key_id is not None:
            session_kwargs["aws_access_key_id"] = config.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = config.aws_secret_access_key
        if config.aws_session_token is not None:
            session_kwargs["aws_session_token"] = config.aws_session_token
        if config.profile_name is not None:
            session_kwargs["profile_name"] = config.profile_name

        client_kwargs: dict[str, Any] = {}
        if config.endpoint_url is not None:
            client_kwargs["endpoint_url"] = config.endpoint_url
        if config.verify_ssl is not None:
            client_kwargs["verify"] = config.verify_ssl
        client_kwargs["config"] = BotoConfig(
            connect_timeout=config.connect_timeout,
            read_timeout=config.read_timeout,
            retries={
                "mode": "standard",
                "total_max_attempts": config.max_attempts,
            },
            s3={"addressing_style": config.addressing_style},
        )

        session = boto3.Session(**session_kwargs)
        return session.client("s3", **client_kwargs)
