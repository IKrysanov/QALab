"""Доменные исключения S3-клиента."""

from typing import Optional


class S3ClientError(RuntimeError):
    """Базовая ошибка S3-клиента."""


class S3ConfigurationError(S3ClientError, ValueError):
    """Конфигурация S3 отсутствует или противоречива."""


class S3DependencyError(S3ClientError, ImportError):
    """Не установлена библиотека, необходимая для работы S3-клиента."""


class S3ClientClosedError(S3ClientError):
    """Операция вызвана после закрытия S3-клиента."""


class S3ObjectTooLargeError(S3ClientError):
    """Объект превышает установленный предел загрузки в память."""

    def __init__(
            self,
            bucket: str,
            object_key: str,
            max_size: int,
            *,
            actual_size: Optional[int] = None,
    ) -> None:
        self.bucket = bucket
        self.object_key = object_key
        self.max_size = max_size
        self.actual_size = actual_size

        message = (
            "S3 object exceeds in-memory download limit: "
            f"target='s3://{bucket}/{object_key}', max_size={max_size}"
        )
        if actual_size is not None:
            message = f"{message}, actual_size={actual_size}"
        super().__init__(message)


class S3OperationError(S3ClientError):
    """Ошибка операции в S3 с безопасным контекстом без учётных данных."""

    def __init__(
            self,
            operation: str,
            bucket: str,
            object_key: Optional[str] = None,
            *,
            cause_type: Optional[str] = None,
            error_code: Optional[str] = None,
            http_status: Optional[int] = None,
            request_id: Optional[str] = None,
    ) -> None:
        self.operation = operation
        self.bucket = bucket
        self.object_key = object_key
        self.cause_type = cause_type
        self.error_code = error_code
        self.http_status = http_status
        self.request_id = request_id

        target = f"s3://{bucket}"
        if object_key is not None:
            target = f"{target}/{object_key}"

        details = [
            f"operation={operation!r}",
            f"target={target!r}",
        ]
        if cause_type is not None:
            details.append(f"cause_type={cause_type!r}")
        if error_code is not None:
            details.append(f"error_code={error_code!r}")
        if http_status is not None:
            details.append(f"http_status={http_status}")
        if request_id is not None:
            details.append(f"request_id={request_id!r}")
        super().__init__(f"S3 operation failed: {', '.join(details)}")
