"""Минимальные интерфейсы зависимостей S3-клиента."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol

from .config import S3Config


class S3Service(Protocol):
    """Используемая клиентом часть boto3 S3 API.

    Протокол не привязывает прикладной клиент к конкретному boto3-классу и
    позволяет передавать лёгкий fake/stub в unit-тестах.
    """

    def upload_file(
            self,
            Filename: str,
            Bucket: str,
            Key: str,
            ExtraArgs: Mapping[str, Any],
    ) -> Any:
        ...

    def download_file(
            self,
            Bucket: str,
            Key: str,
            Filename: str,
            ExtraArgs: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        ...

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]:
        ...

    def get_object(self, **kwargs: Any) -> Mapping[str, Any]:
        ...

    def delete_object(self, **kwargs: Any) -> Mapping[str, Any]:
        ...

    def head_object(self, **kwargs: Any) -> Mapping[str, Any]:
        ...

    def list_objects_v2(self, **kwargs: Any) -> Mapping[str, Any]:
        ...

    def generate_presigned_url(
            self,
            ClientMethod: str,
            Params: Mapping[str, Any],
            ExpiresIn: int,
    ) -> str:
        ...

    def close(self) -> None:
        ...


class S3ServiceFactory(Protocol):
    """Фабрика транспорта, отделяющая создание boto3 от S3-операций."""

    def create(self, config: S3Config) -> S3Service:
        ...
