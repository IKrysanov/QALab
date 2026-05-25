"""Общие перечисления и типы для Airflow API v2."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class DagRunState(str, Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"


class DagRunType(str, Enum):
    backfill = "backfill"
    scheduled = "scheduled"
    manual = "manual"
    asset_triggered = "asset_triggered"


class DagRunTriggeredByType(str, Enum):
    cli = "cli"
    operator = "operator"
    rest_api = "rest_api"
    ui = "ui"
    test = "test"
    timetable = "timetable"
    asset = "asset"
    backfill = "backfill"


class TaskInstanceState(str, Enum):
    scheduled = "scheduled"
    queued = "queued"
    running = "running"
    success = "success"
    restarting = "restarting"
    failed = "failed"
    up_for_retry = "up_for_retry"
    up_for_reschedule = "up_for_reschedule"
    upstream_failed = "upstream_failed"
    skipped = "skipped"
    removed = "removed"
    deferred = "deferred"


class ReprocessBehavior(str, Enum):
    none = "none"
    failed = "failed"
    completed = "completed"


class BulkActionOnExistence(str, Enum):
    fail = "fail"
    skip = "skip"
    overwrite = "overwrite"


class BulkActionNotOnExistence(str, Enum):
    fail = "fail"
    skip = "skip"


class TimeDelta(BaseModel):
    """Интервал времени (дни + секунды)."""
    days: Optional[int] = None
    seconds: Optional[int] = None
    microseconds: Optional[int] = None


class HTTPExceptionResponse(BaseModel):
    detail: Any
    status: Optional[int] = None
    type: Optional[str] = None
