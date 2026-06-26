"""Модели мониторинга Airflow Stable REST API v1 (Airflow 2.x): health, version."""

from typing import Optional

from pydantic import BaseModel


# === Version ===

class VersionInfo(BaseModel):
    """Ответ GET /api/v1/version."""

    version: str
    git_version: Optional[str] = None


# === Health ===

class MetadatabaseStatus(BaseModel):
    status: Optional[str] = None


class SchedulerStatus(BaseModel):
    status: Optional[str] = None
    latest_scheduler_heartbeat: Optional[str] = None


class TriggererStatus(BaseModel):
    status: Optional[str] = None
    latest_triggerer_heartbeat: Optional[str] = None


class DagProcessorStatus(BaseModel):
    status: Optional[str] = None
    latest_dag_processor_heartbeat: Optional[str] = None


class HealthInfoResponse(BaseModel):
    """Ответ GET /api/v1/health — состояние компонентов Airflow.

    Все компоненты опциональны: набор зависит от версии/конфигурации
    (например, ``dag_processor`` присутствует не во всех инсталляциях).
    """

    metadatabase: Optional[MetadatabaseStatus] = None
    scheduler: Optional[SchedulerStatus] = None
    triggerer: Optional[TriggererStatus] = None
    dag_processor: Optional[DagProcessorStatus] = None
