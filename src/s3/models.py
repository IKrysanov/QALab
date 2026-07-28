"""Типизированные результаты операций S3."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional


@dataclass(frozen=True)
class S3UploadResult:
    """Данные, подтверждающие загрузку объекта через ``put_object``."""

    object_key: str
    etag: Optional[str] = None
    version_id: Optional[str] = None
    checksums: Mapping[str, str] = field(default_factory=dict)
    request_id: Optional[str] = None


@dataclass(frozen=True)
class S3ObjectMetadata:
    """Метаданные объекта без загрузки его содержимого."""

    object_key: str
    size_bytes: Optional[int] = None
    etag: Optional[str] = None
    version_id: Optional[str] = None
    content_type: Optional[str] = None
    last_modified: Optional[datetime] = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    checksums: Mapping[str, str] = field(default_factory=dict)
    request_id: Optional[str] = None


@dataclass(frozen=True)
class S3DeleteResult:
    """Результат удаления объекта или его конкретной версии."""

    object_key: str
    version_id: Optional[str] = None
    delete_marker: Optional[bool] = None
    request_id: Optional[str] = None
