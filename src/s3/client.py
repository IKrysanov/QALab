"""Высокоуровневые операции с объектами в S3."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Mapping, NoReturn, Optional, Union

from utils.logger import get_logger

from .boto3_factory import Boto3S3ServiceFactory
from .config import S3Config
from .exceptions import S3ClientClosedError, S3OperationError
from .protocols import S3Service, S3ServiceFactory

PathLike = Union[str, Path]

logger = get_logger("s3.client")


class S3Client:
    """Клиент объектных операций с внедряемым S3-транспортом.

    В production транспорт создаёт :class:`Boto3S3ServiceFactory`. В тестах
    можно передать объект, реализующий узкий :class:`S3Service` protocol.
    """

    def __init__(
            self,
            config: S3Config,
            *,
            service: Optional[S3Service] = None,
            service_factory: Optional[S3ServiceFactory] = None,
    ) -> None:
        if service is not None and service_factory is not None:
            raise ValueError("Pass either service or service_factory, not both")

        factory = service_factory or Boto3S3ServiceFactory()
        self._config = config
        self._service = service if service is not None else factory.create(config)
        self._owns_service = service is None
        self._closed = False

    @property
    def bucket_name(self) -> str:
        return self._config.bucket_name

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> "S3Client":
        self._ensure_open()
        return self

    def __exit__(
            self,
            exc_type: Optional[type[BaseException]],
            exc: Optional[BaseException],
            traceback: Optional[TracebackType],
    ) -> None:
        try:
            self.close()
        except S3OperationError:
            if exc_type is None:
                raise
            logger.error(
                "event=s3_client_close_error_suppressed bucket=%s "
                "original_exception=%s",
                self.bucket_name,
                exc_type.__name__,
            )

    def close(self) -> None:
        """Идемпотентно закрыть принадлежащий клиенту boto3-транспорт."""

        if self._closed:
            return

        try:
            if self._owns_service:
                self._service.close()
        except Exception as exc:
            self._raise_operation_error("close", None, exc)
        finally:
            self._closed = True

        logger.info(
            "event=s3_client_closed bucket=%s owns_service=%s",
            self.bucket_name,
            str(self._owns_service).lower(),
        )

    def upload_file(
            self,
            source_path: PathLike,
            object_key: str,
            *,
            extra_args: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Загрузить локальный файл по ``object_key`` внутри текущего bucket."""

        self._ensure_open()
        self._validate_object_key(object_key)
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        try:
            self._service.upload_file(
                Filename=str(source),
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=dict(extra_args or {}),
            )
        except Exception as exc:
            self._raise_operation_error("upload_file", object_key, exc)
        self._log_success("upload_file", object_key)

    def upload_bytes(
            self,
            data: bytes,
            object_key: str,
            *,
            content_type: Optional[str] = None,
            metadata: Optional[Mapping[str, str]] = None,
            extra_args: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Загрузить байты по ``object_key`` внутри текущего bucket."""

        self._ensure_open()
        self._validate_object_key(object_key)
        request: dict[str, Any] = {
            **dict(extra_args or {}),
            "Bucket": self.bucket_name,
            "Key": object_key,
            "Body": data,
        }
        if content_type is not None:
            request["ContentType"] = content_type
        if metadata is not None:
            request["Metadata"] = dict(metadata)

        try:
            self._service.put_object(**request)
        except Exception as exc:
            self._raise_operation_error("put_object", object_key, exc)
        self._log_success("put_object", object_key, size_bytes=len(data))

    def download_file(
            self,
            object_key: str,
            destination_path: PathLike,
    ) -> Path:
        """Скачать объект в файл, создав отсутствующие родительские каталоги."""

        self._ensure_open()
        self._validate_object_key(object_key)
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._service.download_file(
                Bucket=self.bucket_name,
                Key=object_key,
                Filename=str(destination),
            )
        except Exception as exc:
            self._raise_operation_error("download_file", object_key, exc)
        self._log_success("download_file", object_key)
        return destination

    def download_bytes(self, object_key: str) -> bytes:
        """Скачать объект в память."""

        self._ensure_open()
        self._validate_object_key(object_key)
        body = None
        operation_error: Optional[Exception] = None
        close_error: Optional[Exception] = None
        data: Optional[bytes] = None
        try:
            response = self._service.get_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            body = response["Body"]
            data = body.read()
        except Exception as exc:
            operation_error = exc

        if body is not None:
            close = getattr(body, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:
                    close_error = exc

        if operation_error is not None:
            self._raise_operation_error(
                "get_object",
                object_key,
                operation_error,
            )
        if close_error is not None:
            self._raise_operation_error(
                "close_object_body",
                object_key,
                close_error,
            )
        if not isinstance(data, bytes):
            error = TypeError(
                f"S3 response body must return bytes, got {type(data).__name__}"
            )
            self._raise_operation_error("get_object", object_key, error)

        self._log_success("get_object", object_key, size_bytes=len(data))
        return data

    def delete_object(self, object_key: str) -> None:
        """Удалить объект."""

        self._ensure_open()
        self._validate_object_key(object_key)
        try:
            self._service.delete_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
        except Exception as exc:
            self._raise_operation_error("delete_object", object_key, exc)
        self._log_success("delete_object", object_key)

    def object_exists(self, object_key: str) -> bool:
        """Проверить существование объекта без скачивания его содержимого."""

        self._ensure_open()
        self._validate_object_key(object_key)
        try:
            self._service.head_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            return True
        except Exception as exc:
            if self._is_not_found(exc):
                return False
            self._raise_operation_error("head_object", object_key, exc)

    def list_keys(
            self,
            prefix: str = "",
            *,
            limit: Optional[int] = None,
    ) -> list[str]:
        """Вернуть ключи с префиксом, прозрачно проходя пагинацию S3."""

        self._ensure_open()
        if limit is not None and (
                isinstance(limit, bool)
                or not isinstance(limit, int)
                or limit < 1
        ):
            raise ValueError("limit must be greater than zero")

        keys: list[str] = []
        continuation_token: Optional[str] = None
        seen_tokens: set[str] = set()

        while True:
            request: dict[str, Any] = {
                "Bucket": self.bucket_name,
                "Prefix": prefix,
            }
            if continuation_token is not None:
                request["ContinuationToken"] = continuation_token
            if limit is not None:
                request["MaxKeys"] = min(1000, limit - len(keys))

            try:
                response = self._service.list_objects_v2(**request)
            except Exception as exc:
                self._raise_operation_error("list_objects_v2", prefix or None, exc)

            keys.extend(
                item["Key"]
                for item in response.get("Contents", [])
                if "Key" in item
            )
            if limit is not None and len(keys) >= limit:
                return keys[:limit]
            if not response.get("IsTruncated", False):
                return keys

            continuation_token = response.get("NextContinuationToken")
            if not continuation_token:
                error = RuntimeError(
                    "S3 returned a truncated page without NextContinuationToken"
                )
                self._raise_operation_error(
                    "list_objects_v2",
                    prefix or None,
                    error,
                )
            if continuation_token in seen_tokens:
                error = RuntimeError(
                    "S3 returned a repeated NextContinuationToken"
                )
                self._raise_operation_error(
                    "list_objects_v2",
                    prefix or None,
                    error,
                )
            seen_tokens.add(continuation_token)

    def generate_presigned_url(
            self,
            object_key: str,
            *,
            expires_in: int = 3600,
            operation: str = "get_object",
    ) -> str:
        """Создать временную ссылку для GET или PUT объекта."""

        self._ensure_open()
        self._validate_object_key(object_key)
        if operation not in {"get_object", "put_object"}:
            raise ValueError("operation must be 'get_object' or 'put_object'")
        if expires_in < 1:
            raise ValueError("expires_in must be greater than zero")

        try:
            return self._service.generate_presigned_url(
                ClientMethod=operation,
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            self._raise_operation_error(
                "generate_presigned_url",
                object_key,
                exc,
            )

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        response = getattr(exc, "response", {})
        if not isinstance(response, Mapping):
            return False

        error = response.get("Error", {})
        metadata = response.get("ResponseMetadata", {})
        code = error.get("Code") if isinstance(error, Mapping) else None
        status = (
            metadata.get("HTTPStatusCode")
            if isinstance(metadata, Mapping)
            else None
        )
        normalized_code = str(code) if code is not None else None
        if normalized_code == "NoSuchBucket":
            return False
        if normalized_code is not None:
            return normalized_code in {"404", "NoSuchKey", "NotFound"}
        return status == 404

    def _raise_operation_error(
            self,
            operation: str,
            object_key: Optional[str],
            exc: Exception,
    ) -> NoReturn:
        error_code, http_status, request_id = self._sdk_error_details(exc)
        logger.warning(
            "event=s3_operation_failed operation=%s target=%s "
            "cause_type=%s error_code=%s http_status=%s request_id=%s",
            operation,
            self._target(object_key),
            type(exc).__name__,
            error_code or "-",
            http_status if http_status is not None else "-",
            request_id or "-",
        )
        raise S3OperationError(
            operation,
            self.bucket_name,
            object_key,
            cause_type=type(exc).__name__,
            error_code=error_code,
            http_status=http_status,
            request_id=request_id,
        ) from exc

    def _log_success(
            self,
            operation: str,
            object_key: str,
            *,
            size_bytes: Optional[int] = None,
    ) -> None:
        logger.info(
            "event=s3_operation_succeeded operation=%s target=%s size_bytes=%s",
            operation,
            self._target(object_key),
            size_bytes if size_bytes is not None else "-",
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise S3ClientClosedError(
                f"S3 client is closed: bucket={self.bucket_name!r}"
            )

    @staticmethod
    def _validate_object_key(object_key: str) -> None:
        if not object_key:
            raise ValueError("S3 object key must not be empty")

    def _target(self, object_key: Optional[str]) -> str:
        target = f"s3://{self.bucket_name}"
        return (
            f"{target}/{object_key}"
            if object_key is not None
            else target
        )

    @staticmethod
    def _sdk_error_details(
            exc: Exception,
    ) -> tuple[Optional[str], Optional[int], Optional[str]]:
        response = getattr(exc, "response", {})
        if not isinstance(response, Mapping):
            return None, None, None

        error = response.get("Error", {})
        metadata = response.get("ResponseMetadata", {})

        error_code = error.get("Code") if isinstance(error, Mapping) else None
        http_status = (
            metadata.get("HTTPStatusCode")
            if isinstance(metadata, Mapping)
            else None
        )
        request_id = (
            metadata.get("RequestId")
            if isinstance(metadata, Mapping)
            else None
        )
        return (
            str(error_code) if error_code is not None else None,
            http_status if isinstance(http_status, int) else None,
            str(request_id) if request_id is not None else None,
        )
